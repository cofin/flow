---
name: ipc
description: "Zero-copy IPC patterns: shared memory regions, SPSC/MPMC ring buffers, platform sync primitives, notification mechanisms, and cross-process coordination. Use when implementing IPC primitives or high-performance data transfer."
---

# IPC (Inter-Process Communication)

## Scope

- Shared memory regions (POSIX `shm_open` + `mmap`, Windows `CreateFileMapping`).
- Lock-free ring buffers (SPSC, MPMC).
- Platform-specific synchronization (futex, ulock, Win32 Event).
- Notification mechanisms (eventfd, pipe, kqueue).
- Async ring integration with Tokio.
- Buffer pools and zero-copy data transfer.

## Shared Memory Regions

### ShmRegion Pattern

```rust
pub struct ShmRegion {
    ptr: *mut u8,
    len: usize,
    fd: OwnedFd,  // RAII: closes on drop
}

impl ShmRegion {
    pub fn create(name: &str, size: usize) -> Result<Self, IpcError> {
        // SAFETY: shm_open + ftruncate + mmap is the standard POSIX pattern.
        // We own the fd exclusively and unlink after mapping.
        unsafe {
            let fd = shm_open(name, O_CREAT | O_RDWR, 0o600)?;
            ftruncate(fd, size as libc::off_t)?;
            let ptr = mmap(
                std::ptr::null_mut(),
                size,
                PROT_READ | PROT_WRITE,
                MAP_SHARED,
                fd,
                0,
            )?;
            shm_unlink(name)?;  // Unlink immediately — fd keeps it alive
            Ok(Self { ptr: ptr.cast(), len: size, fd: OwnedFd(fd) })
        }
    }

    pub fn as_slice(&self) -> &[u8] {
        // SAFETY: ptr is valid for len bytes and region outlives self
        unsafe { std::slice::from_raw_parts(self.ptr, self.len) }
    }
}

impl Drop for ShmRegion {
    fn drop(&mut self) {
        // SAFETY: We own this mapping exclusively
        unsafe { munmap(self.ptr.cast(), self.len) };
        // fd closed by OwnedFd::drop
    }
}
```

### Key Rules

- Always unlink shared memory names immediately after mapping (prevents leaks on crash).
- Use RAII for both the mapping and the file descriptor.
- Align region sizes to page boundaries (`sysconf(_SC_PAGESIZE)`).

## Ring Buffers

### SPSC (Single-Producer, Single-Consumer)

```rust
#[repr(C, align(64))]  // Cache-line aligned
pub struct SpscHeader {
    write_pos: AtomicU64,
    _pad1: [u8; 56],     // Prevent false sharing
    read_pos: AtomicU64,
    _pad2: [u8; 56],
    capacity: u64,        // Must be power of two
}

impl SpscRing {
    pub fn push(&self, data: &[u8]) -> Result<(), RingError> {
        let write = self.header.write_pos.load(Ordering::Relaxed);
        let read = self.header.read_pos.load(Ordering::Acquire);
        let available = self.header.capacity - (write - read);

        if data.len() as u64 > available {
            return Err(RingError::Full);
        }

        let offset = (write % self.header.capacity) as usize;
        // SAFETY: Bounds checked above, single writer
        unsafe { self.write_at(offset, data) };

        self.header.write_pos.store(write + data.len() as u64, Ordering::Release);
        Ok(())
    }
}
```

### MPMC (Multi-Producer, Multi-Consumer)

- Use sequence numbers per slot for lock-free coordination.
- Each slot has an `AtomicU64` sequence tag.
- Producers CAS the sequence to claim a slot; consumers CAS to consume.

### Design Rules

- Capacity **must** be a power of two (use bitwise AND for modulo).
- Align headers to cache lines (64 bytes) to prevent false sharing.
- Separate read and write positions with padding.
- Use `Ordering::Acquire` for reads, `Ordering::Release` for writes.
- Validate bounds on every read/write — never trust offsets from shared memory.

## Platform Sync Primitives

Implement behind a trait for portability:

```rust
pub trait Notifier: Send + Sync {
    fn notify(&self) -> Result<(), IpcError>;
    fn wait(&self, timeout: Option<Duration>) -> Result<(), IpcError>;
}
```

### Linux: eventfd

```rust
pub struct EventFdNotifier {
    fd: OwnedFd,
}

impl Notifier for EventFdNotifier {
    fn notify(&self) -> Result<(), IpcError> {
        let val: u64 = 1;
        // SAFETY: fd is valid, writing 8 bytes to eventfd
        unsafe { libc::write(self.fd.0, &val as *const u64 as *const _, 8) };
        Ok(())
    }

    fn wait(&self, timeout: Option<Duration>) -> Result<(), IpcError> {
        // Use poll() with timeout, then read the eventfd
        let mut buf: u64 = 0;
        unsafe { libc::read(self.fd.0, &mut buf as *mut u64 as *mut _, 8) };
        Ok(())
    }
}
```

### macOS: pipe or kqueue

- Use `pipe()` pair for simple notification (write 1 byte to wake).
- Use `kqueue` + `EVFILT_USER` for more advanced signaling.

### Windows: Win32 Event

- `CreateEventW` / `SetEvent` / `WaitForSingleObject`.

## Async Ring (Tokio Integration)

Wrap ring buffers for async producers/consumers:

```rust
pub struct AsyncRing {
    ring: SpscRing,
    notify: Arc<tokio::sync::Notify>,
}

impl AsyncRing {
    pub async fn push(&self, data: &[u8]) -> Result<(), RingError> {
        loop {
            match self.ring.push(data) {
                Ok(()) => {
                    self.notify.notify_one();
                    return Ok(());
                }
                Err(RingError::Full) => {
                    // Yield and retry
                    tokio::task::yield_now().await;
                }
                Err(e) => return Err(e),
            }
        }
    }

    pub async fn pop(&self, buf: &mut [u8]) -> Result<usize, RingError> {
        loop {
            match self.ring.pop(buf) {
                Ok(n) => return Ok(n),
                Err(RingError::Empty) => {
                    self.notify.notified().await;
                }
                Err(e) => return Err(e),
            }
        }
    }
}
```

## Guard Pattern (RAII Cleanup)

Use RAII guards for operations that need cleanup on scope exit:

```rust
pub struct MappedGuard<'a> {
    region: &'a ShmRegion,
    offset: usize,
    len: usize,
}

impl<'a> MappedGuard<'a> {
    pub fn as_slice(&self) -> &[u8] {
        &self.region.as_slice()[self.offset..self.offset + self.len]
    }
}

impl<'a> Drop for MappedGuard<'a> {
    fn drop(&mut self) {
        // Release the region slice back to the pool
        self.region.release(self.offset, self.len);
    }
}
```

## Testing

- **Multi-process tests:** Fork parent/child to test shared memory across process boundaries.
- **Property tests:** `proptest` for FIFO ordering, no-loss, and no-duplication invariants.
- **Stress tests:** Concurrent producer/consumer with `loom` for atomic ordering verification.
- **Miri:** Run on all unsafe code paths: `cargo +nightly miri test`.
- **Sanitizers:** ThreadSanitizer for data race detection in ring buffers.

## Performance Targets

| Metric | Target |
|--------|--------|
| Shared memory latency | < 10 us |
| Ring buffer throughput | > 1M msg/sec |
| Zero-copy overhead | < 1 us per transfer |

Measure with `criterion` and record baselines before optimizing.

## Conventions

- Separate control plane (small metadata) from data plane (bulk shared memory).
- Use explicit versioning in shared memory headers for protocol evolution.
- Enforce single-writer semantics in SPSC — document clearly if MPMC.
- Prefer `rustix` over raw `libc` for cleaner POSIX bindings.

## Official References

- https://doc.rust-lang.org/std/os/fd/struct.OwnedFd.html
- https://docs.rs/crate/rustix/latest
- https://man7.org/linux/man-pages/man3/shm_open.3.html
- https://man7.org/linux/man-pages/man2/eventfd.2.html
- https://docs.rs/tokio/latest/tokio/sync/struct.Notify.html
- https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-createfilemappingw

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Rust](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/rust.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
