# Performance Review Checklist

Work through each category. Flag anything that looks like a real bottleneck. For each finding: identify the problem, specify what metric would show improvement, and estimate the rough impact. Skip categories that clearly don't apply to the code under review.

1. **Query patterns** — N+1 queries? Missing indexes? Full table scans? Unbounded result sets? Unnecessary joins that could be deferred?

2. **Memory** — Large allocations inside loops? Unbounded collections that grow with input size? References held longer than needed? Missing pagination on large result sets?

3. **I/O** — Synchronous I/O in async code paths? Sequential operations that could run in parallel? Missing connection pooling? Unbatched network calls that could be batched?

4. **Caching** — Repeated expensive computations with the same inputs? Missing cache for stable or slowly-changing data? Cache invalidation correctness — are stale entries possible?

5. **Algorithmic** — O(n²) or worse on variable-size input? Linear scans where a lookup table or index would work? Sorting inside a loop that could be sorted once?

6. **Concurrency** — Lock contention on shared resources? Shared mutable state in hot paths? Thread pool or connection pool exhaustion under load?

7. **Resource lifecycle** — Connection leaks? File handle leaks? Missing cleanup in error paths that leaves resources open?

8. **Measurement** — Are there metrics or tracing in place to detect regressions? Can the impact of this change be measured before and after? If not, recommend adding instrumentation before optimizing.
