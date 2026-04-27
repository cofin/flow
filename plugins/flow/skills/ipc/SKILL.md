---
name: ipc
description: "Use when implementing inter-process communication, shared memory regions, SPSC or MPMC ring buffers, zero-copy data transfer, platform synchronization primitives, or process notification mechanisms."
---

# IPC (Inter-Process Communication)

## Scope

- Shared memory regions (POSIX `shm_open` + `mmap`, Windows `CreateFileMapping`).
- Lock-free ring buffers (SPSC, MPMC).
- Platform-specific synchronization (futex, ulock, Win32 Event).
- Notification mechanisms (eventfd, pipe, kqueue).
- Async ring integration with Tokio.
- Buffer pools and zero-copy data transfer.

<workflow>

## Shared Memory Regions

### ShmRegion Pattern

<example>

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

</example>

<guardrails>
## Guardrails

- **Always unlink shared memory immediately** -- Use `shm_unlink` as soon as the memory is mapped to ensure it is correctly cleaned up by the OS when the process exits.
- **Use RAII for all resources** -- Wrap pointers, file descriptors, and mapping handles in structs that implement `Drop` to prevent resource leaks on crash or error.
- **Align to page boundaries** -- Shared memory region sizes should always be a multiple of the system page size (typically 4096 bytes) for optimal mapping.
- **Capacity must be a power of two** -- For ring buffers, this allows for fast indexing using bitwise AND instead of expensive modulo operations.
- **Align headers to cache lines (64 bytes)** -- This prevents false sharing between producers and consumers on different CPU cores.
</guardrails>

<validation>
## Validation Checkpoint

- [ ] Shared memory is unlinked immediately after mapping
- [ ] RAII cleanup logic is implemented in `Drop` for all resources
- [ ] Ring buffer capacity is a power of two
- [ ] Headers are cache-line aligned (64 bytes) with explicit padding
- [ ] Bounds checks are performed on all reads and writes from shared memory
- [ ] Atomic memory ordering is correctly applied (`Acquire`/`Release`)
</validation>
