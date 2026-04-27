# Platform Abstraction

## Conditional Modules

Use `#[cfg(target_os = "...")]` to compile platform-specific modules. Provide a common interface via re-exports:

```rust
//! platform/mod.rs — Platform-specific wait/wake primitives.

#[cfg(target_os = "linux")]
pub mod linux;
#[cfg(target_os = "macos")]
pub mod macos;
#[cfg(windows)]
pub mod windows;

#[cfg(target_os = "linux")]
pub(crate) use linux::{wait_on_address, wait_on_address_timeout, wake_all, wake_one};
#[cfg(target_os = "macos")]
pub(crate) use macos::{wait_on_address, wait_on_address_timeout, wake_all, wake_one};
#[cfg(windows)]
pub(crate) use windows::{wait_on_address, wait_on_address_timeout, wake_all, wake_one};

// Unsupported platform fallback
#[cfg(not(any(target_os = "linux", target_os = "macos", windows)))]
pub(crate) fn wait_on_address(
    _word: &core::sync::atomic::AtomicU32,
    _expected: u32,
) -> Result<(), crate::sync::SyncError> {
    Err(crate::sync::SyncError::Unsupported)
}
```

## Target-Specific Dependencies

Use `[target]` sections in Cargo.toml for OS-specific deps:

```toml
[target.'cfg(unix)'.dependencies]
libc = { workspace = true }
rustix = { workspace = true, features = ["fs"] }

[target.'cfg(windows)'.dependencies]
windows-sys = { workspace = true }
```

## Linux: futex Syscalls

Use `libc::SYS_futex` for wait/wake. Always check for `EAGAIN`/`EINTR`:

```rust
use core::sync::atomic::AtomicU32;
use std::io;
use crate::sync::SyncError;

pub(crate) fn wait_on_address(word: &AtomicU32, expected: u32) -> Result<(), SyncError> {
    let addr = word as *const AtomicU32 as *const u32;
    // SAFETY: futex syscall on a valid aligned u32 address.
    let res = unsafe {
        libc::syscall(
            libc::SYS_futex,
            addr,
            libc::FUTEX_WAIT,
            expected,
            std::ptr::null::<libc::timespec>(),
        )
    } as i64;
    if res == 0 {
        return Ok(());
    }
    let err = io::Error::last_os_error();
    match err.raw_os_error() {
        Some(libc::EAGAIN) | Some(libc::EINTR) => Ok(()),
        _ => Err(SyncError::Syscall(err)),
    }
}

pub(crate) fn wake_one(word: &AtomicU32) -> Result<(), SyncError> {
    let addr = word as *const AtomicU32 as *const u32;
    // SAFETY: futex wake on a valid aligned u32 address.
    let res = unsafe { libc::syscall(libc::SYS_futex, addr, libc::FUTEX_WAKE, 1) } as i64;
    if res >= 0 { Ok(()) }
    else { Err(SyncError::Syscall(io::Error::last_os_error())) }
}
```

Linux-specific syscalls like `pidfd_open`:

```rust
use std::os::fd::{FromRawFd, OwnedFd};

/// Open a process file descriptor for monitoring process lifetime.
/// Available on Linux 5.3+ (kernel `pidfd_open(2)`).
pub fn pidfd_open(pid: i32) -> io::Result<OwnedFd> {
    let fd = unsafe { libc::syscall(libc::SYS_pidfd_open, pid, 0) } as i32;
    if fd < 0 {
        return Err(io::Error::last_os_error());
    }
    // SAFETY: pidfd_open returns a valid FD on success.
    Ok(unsafe { OwnedFd::from_raw_fd(fd) })
}
```

## macOS: ulock (Feature-Gated)

Feature-gate ulock behind `macos-ulock`. Default to spin+nanosleep fallback:

```rust
//! macOS-specific primitives (ulock fast-path, spin+sleep fallback).

use core::sync::atomic::{AtomicU32, Ordering};
use std::time::{Duration, Instant};
use crate::sync::SyncError;

const SPIN_ITERS: usize = 1024;
const SLEEP_NS: i64 = 1_000_000; // 1ms

pub(crate) fn wait_on_address(word: &AtomicU32, expected: u32) -> Result<(), SyncError> {
    #[cfg(feature = "macos-ulock")]
    { return ulock_wait(word, expected); }
    spin_sleep_wait(word, expected)
}

fn spin_sleep_wait(word: &AtomicU32, expected: u32) -> Result<(), SyncError> {
    let mut spins = 0usize;
    loop {
        if word.load(Ordering::Acquire) != expected {
            return Ok(());
        }
        if spins < SPIN_ITERS {
            spins += 1;
            std::hint::spin_loop();
            continue;
        }
        let ts = libc::timespec { tv_sec: 0, tv_nsec: SLEEP_NS };
        unsafe { libc::nanosleep(&ts, std::ptr::null_mut()); }
    }
}

#[cfg(feature = "macos-ulock")]
extern "C" {
    fn __ulock_wait(operation: u32, addr: *const u32, value: u64, timeout: u32) -> i32;
    fn __ulock_wake(operation: u32, addr: *const u32, wake_value: u64) -> i32;
}
```

## Windows: WaitOnAddress

Use `windows-sys` for kernel wait/wake primitives:

```rust
use windows_sys::Win32::Foundation::{GetLastError, ERROR_TIMEOUT};
use windows_sys::Win32::System::Threading::{WaitOnAddress, WakeByAddressSingle, WakeByAddressAll};

pub(crate) fn wait_on_address(word: &AtomicU32, expected: u32) -> Result<(), SyncError> {
    let expected_val = expected;
    // SAFETY: WaitOnAddress on a valid aligned u32 address.
    let res = unsafe {
        WaitOnAddress(
            word as *const AtomicU32 as *const core::ffi::c_void,
            &expected_val as *const u32 as *const core::ffi::c_void,
            core::mem::size_of::<u32>(),
            u32::MAX,
        )
    };
    if res == 0 {
        return Err(SyncError::Syscall(io::Error::from_raw_os_error(
            unsafe { GetLastError() } as i32,
        )));
    }
    Ok(())
}

pub(crate) fn wake_one(word: &AtomicU32) -> Result<(), SyncError> {
    unsafe { WakeByAddressSingle(word as *const AtomicU32 as *const core::ffi::c_void) };
    Ok(())
}
```

## Shared Memory (Cross-Platform)

Use platform handles with RAII cleanup:

```rust
#[cfg(unix)]
pub type ShmHandle = std::os::fd::RawFd;
#[cfg(windows)]
pub type ShmHandle = std::os::windows::io::RawHandle;

pub struct ShmRegion {
    ptr: NonNull<u8>,
    len: usize,
    handle: ShmHandle,
    owns_handle: bool,
    owns_mapping: bool,
}

impl Drop for ShmRegion {
    fn drop(&mut self) {
        unsafe {
            #[cfg(unix)]
            {
                if self.owns_mapping { libc::munmap(self.ptr.as_ptr().cast(), self.len); }
                if self.owns_handle { libc::close(self.handle); }
            }
            #[cfg(windows)]
            {
                use windows_sys::Win32::Foundation::CloseHandle;
                use windows_sys::Win32::System::Memory::UnmapViewOfFile;
                if self.owns_mapping { UnmapViewOfFile(self.ptr.as_ptr().cast()); }
                if self.owns_handle { CloseHandle(self.handle); }
            }
        }
    }
}
```

## Unsafe Discipline

- Document every `unsafe` block with a `// SAFETY:` comment.
- Isolate platform-specific unsafe in `platform/` modules behind safe wrappers.
- Prefer `rustix` over raw `libc` for POSIX syscalls when available (e.g., `rustix::fs::flock`).
- Specify atomic `Ordering` explicitly. Never default to `SeqCst` without justification.
- Use RAII wrappers for OS handles (fd, mmap, socket).
