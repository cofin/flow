# Cloud Run GPU Support

## Overview

Cloud Run supports GPU acceleration for ML inference workloads. GPUs are attached to instances on a per-service or per-job basis.

## Available GPU Types

### NVIDIA L4

```bash
gcloud run deploy SERVICE \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --cpu=8 \
  --memory=32Gi \
  --region=us-central1
```

- Minimum: 4 CPU, 16 GiB memory
- Recommended: 8 CPU, 32 GiB memory
- Driver: NVIDIA 535.x (pre-installed)
- VRAM: 24 GB

### NVIDIA RTX PRO 6000 Blackwell (Preview)

```bash
gcloud run deploy SERVICE \
  --gpu=1 \
  --gpu-type=nvidia-rtx-pro-6000-blackwell \
  --cpu=20 \
  --memory=80Gi \
  --region=us-central1
```

- Minimum: 20 CPU, 80 GiB memory
- Driver: NVIDIA 580.x (pre-installed)
- VRAM: 96 GB

## Driver and Library Setup

Drivers are pre-installed — no custom driver installation needed in your Dockerfile.

- `LD_LIBRARY_PATH` is automatically configured
- NVIDIA libraries available at `/usr/local/nvidia/lib64`
- CUDA toolkit accessible without additional setup

## ML Inference Best Practices

### Model Storage

- **Download models from GCS, not baked into the image** for models >10 GB
  - Use `gsutil cp` or the GCS FUSE volume mount at startup
  - Keeps image size manageable and model updates independent of deployments
- Use **GGUF format** for fast loading with llama.cpp-based frameworks
- **Pre-quantize to 4-bit** (Q4_K_M recommended) for better memory efficiency and concurrency

### Warm-Up

- Pre-warm LLM caches at container startup before serving traffic
- Use startup probes (see `volumes.md`) to hold traffic until the model is loaded
- Consider semantic caching (e.g., Redis or in-memory LRU) for repeated queries

### Serving Frameworks

| Framework | Best For | Notes |
|-----------|----------|-------|
| **vLLM** | Production serving | PagedAttention, continuous batching, OpenAI-compatible API |
| **Ollama** | Simple serving | Easy model management, good for dev/staging |
| **llama.cpp server** | CPU/GPU hybrid | GGUF-native, low overhead |

### Example: vLLM Deployment

```bash
gcloud run deploy llm-service \
  --image=gcr.io/my-project/vllm-app:latest \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --cpu=8 \
  --memory=32Gi \
  --concurrency=4 \
  --min-instances=1 \
  --max-instances=3 \
  --region=us-central1 \
  --service-account=llm-sa@my-project.iam.gserviceaccount.com
```

## Concurrency Tuning

GPU workloads require explicit concurrency settings — Cloud Run cannot auto-scale based on GPU utilization.

**Formula:**

```
--concurrency = (model_instances × parallel_queries) + (model_instances × batch_size)
```

**Guidance:**

- Set `--concurrency` explicitly — the default (80) is too high for GPU workloads
- For single-model, non-batched inference: start with `--concurrency=1` to `--concurrency=4`
- For batched inference (vLLM continuous batching): concurrency can be higher (8–16)
- Test under load and monitor GPU memory utilization (`nvidia-smi`)

## GPU for Cloud Run Jobs

GPU flags work identically for Jobs. Add the zonal redundancy annotation to ensure scheduling:

```bash
gcloud run jobs deploy gpu-batch-job \
  --image=IMAGE_URL \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --cpu=8 \
  --memory=32Gi \
  --parallelism=2 \
  --tasks=10 \
  --region=us-central1

# Required annotation for GPU jobs
gcloud run jobs update gpu-batch-job \
  --update-annotations=run.googleapis.com/gpu-zonal-redundancy-disabled=true \
  --region=us-central1
```

**Quota planning:** GPU quota must cover `GPUs × parallelism`. For 2-parallel tasks with 1 GPU each, you need quota for 2 GPUs.

## References

- <https://cloud.google.com/run/docs/configuring/services/gpu>
- <https://cloud.google.com/run/docs/release-notes>
