# Cloud Run Performance

## Cold Start Optimization

### Strategies

1. **Minimum Instances**: Keep containers warm

```bash
gcloud run deploy SERVICE --min-instances=1
```

1. **Startup CPU Boost**: Temporarily increase CPU during startup

```bash
gcloud run deploy SERVICE --cpu-boost
```

1. **Application Optimization**:
   - Use minimal base images (Alpine, Distroless)
   - Lazy-load heavy dependencies
   - Defer non-critical initialization
   - Move heavy operations to background threads

2. **Image Optimization**:
   - Image size doesn't affect cold start directly
   - Focus on reducing initialization complexity
   - Pre-compile bytecode (Python: `--compile-bytecode`)

## Resource Configuration

### CPU and Memory

```bash
# CPU options: 1, 2, 4, 6, 8 vCPUs
gcloud run deploy SERVICE --cpu=2

# Memory: 128Mi to 32Gi
gcloud run deploy SERVICE --memory=2Gi

# Combined
gcloud run deploy SERVICE --cpu=2 --memory=4Gi
```

### Memory Formula

```text
Peak Memory = Standing Memory + (Memory per Request × Concurrency)
```

### GPU Support (Preview)

```bash
gcloud run deploy SERVICE \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --cpu=8 \
  --memory=32Gi
```

## Concurrency Tuning

### Understanding Concurrency

- **Default**: 80 concurrent requests per instance
- **Maximum**: 1000 concurrent requests per instance
- **Minimum**: 1 (single-threaded apps)

### Tuning Guidelines

| Workload Type | Recommended Concurrency |
|---------------|------------------------|
| I/O-bound async | 80-1000 |
| CPU-intensive | 1-10 |
| Memory-intensive | 10-20 |
| Mixed workloads | 20-50 |

```bash
# Set concurrency
gcloud run deploy SERVICE --concurrency=80

# Single-threaded mode
gcloud run deploy SERVICE --concurrency=1
```

### Language-Specific Notes

**Python**: Set `THREADS` environment variable equal to concurrency

```bash
gcloud run deploy SERVICE --set-env-vars="THREADS=80" --concurrency=80
```

**Node.js**: Use async patterns; single-threaded but handles concurrent I/O well

## Best Practices

### Cost Optimization

1. **Use appropriate concurrency** - Higher concurrency = fewer instances = lower cost
2. **Set min-instances wisely** - Balance cold starts vs always-on cost
3. **Use request-based CPU** unless you need background processing
4. **Right-size CPU/memory** - Don't over-provision

### Performance

1. **Enable startup CPU boost** for faster cold starts
2. **Use health probes** to ensure readiness before receiving traffic
3. **Optimize container startup** - lazy load, async init
4. **Use regional deployments** close to users
