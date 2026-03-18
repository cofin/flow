# Mojo Performance Optimization

## SIMD-First Vectorization

Replace scalar loops with SIMD operations for hardware acceleration.

```mojo
from algorithm import vectorize

fn relu_simd(inout tensor: Tensor[DType.float32]):
    alias simd_width = simdwidthof[DType.float32]()
    let zero = SIMD[DType.float32, simd_width](0)

    @parameter
    fn _relu[width: Int](idx: Int):
        let val = tensor.load[width=width](idx)
        tensor.store(idx, val.max(zero))

    vectorize[_relu, simd_width](tensor.num_elements())
```

**Rules:**
- Use `simdwidthof` to auto-detect hardware SIMD width.
- Use `@parameter` for compile-time loop specialization.

---

## GIL-Free Parallelism

True multi-core scaling without Python's GIL.

```mojo
from algorithm import parallelize

fn parallel_transform(inout data: Tensor[DType.float32], num_workers: Int):
    let chunk_size = data.num_elements() // num_workers

    @parameter
    fn _worker(worker_id: Int):
        let start = worker_id * chunk_size
        let end = min(start + chunk_size, data.num_elements())
        for i in range(start, end):
            data[i] = expensive_compute(data[i])

    parallelize[_worker](num_workers)
```
