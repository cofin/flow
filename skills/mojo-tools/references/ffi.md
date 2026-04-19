# C FFI (Foreign Function Interface)

## Static External Calls

Use `external_call` for compile-time linked C functions (e.g., libc).

```mojo
from sys.ffi import external_call

fn get_time() -> Float64:
    return external_call["clock", Float64]()
```

## Dynamic Library Loading (DLHandle)

Load shared libraries at runtime.

```mojo
from sys.ffi import DLHandle

fn load_custom_library():
    var lib = DLHandle("./libcustom_ops.so")
    var compute_fn = lib.get_function[fn (UnsafePointer[Float32], Int) -> Float32]("custom_compute")

    var data = UnsafePointer[Float32].alloc(1024)
    var result = compute_fn(data, 1024)
    data.free()
```

## C Struct Mapping

```mojo
@register_passable("trivial")
struct CTimeSpec:
    var tv_sec: Int64
    var tv_nsec: Int64

    fn __init__(out self):
        self.tv_sec = 0
        self.tv_nsec = 0
```

## Type Mapping

| C Type | Mojo Type |
|--------|-----------|
| `int` / `int32_t` | `Int32` |
| `long` / `int64_t` | `Int64` |
| `float` | `Float32` |
| `void*` | `UnsafePointer[NoneType]` |
