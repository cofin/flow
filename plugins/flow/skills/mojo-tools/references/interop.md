# Zero-Copy Python Interop

## Via __array_interface__

Exchange data with NumPy without copying.

```mojo
fn from_numpy(np_array: PythonObject) -> Tensor[DType.float32]:
    // Extract raw pointer from NumPy's array interface
    let interface = np_array.__array_interface__
    let data_ptr = interface["data"][0].to_int()
    let shape = interface["shape"]

    // SAFETY: np_array must remain alive while this tensor exists.
    let ptr = UnsafePointer[Float32](address=data_ptr)
    return Tensor[DType.float32](ptr, shape[0].to_int())
```

## Returning Data to Python

```mojo
fn to_numpy(tensor: Tensor[DType.float32]) -> PythonObject:
    let np = Python.import_module("numpy")
    return np.frombuffer(
        tensor.data().as_bytes(),
        dtype=np.float32
    ).reshape(tensor.shape())
```

## Python C-API Extensions

### Module Entry Point

```mojo
from python.module import PythonModuleBuilder

@export
fn PyInit_my_module() -> PythonObject:
    var builder = PythonModuleBuilder("my_module")
    builder.add_function("dot_product", dot_product_wrapper)
    return builder.build()
```
