# GPU/TPU Workloads on GKE

## GPU Node Pool Creation

```bash
# Standard cluster: create a GPU node pool
gcloud container node-pools create gpu-pool \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --node-taints=nvidia.com/gpu=present:NoSchedule \
  --num-nodes=0 \
  --enable-autoscaling \
  --min-nodes=0 \
  --max-nodes=10
```

The taint `nvidia.com/gpu=present:NoSchedule` prevents non-GPU pods from consuming GPU node resources.

## GPU Types Reference

| GPU | Machine Series | vCPU Range | Memory | Use Case |
|---|---|---|---|---|
| NVIDIA T4 | N1 | 4–96 | up to 624 GB | Cost-effective inference |
| NVIDIA L4 | G2 | 4–48 | up to 192 GB | Efficient inference/fine-tuning |
| NVIDIA A100 40GB | A2 | 12–96 | up to 1360 GB | Large-scale training, MIG |
| NVIDIA A100 80GB | A2 Ultra | 12–96 | up to 1360 GB | Large-scale training, MIG |
| NVIDIA H100 80GB | A3 | 26–208 | up to 1872 GB | Highest throughput, MIG |

## Autopilot vs Standard for GPU

| Feature | Autopilot | Standard |
|---|---|---|
| Driver install | Automatic | Manual (DaemonSet or GPU Operator) |
| Billing | Pay-per-pod (not per node) | Pay-per-node |
| MIG | Enabled by default (v1.29.3+) | Manual configuration |
| Node management | Google-managed | User-managed |
| GPU Operator | Not needed | `helm install gpu-operator nvidia/gpu-operator` |

**Standard driver install (DaemonSet):**

```bash
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml
```

**Standard driver install (GPU Operator):**

```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace
```

## Pod Spec

GPU resources must be in `limits` only. Kubernetes treats GPU limits as implicit requests -- do not set requests separately or the pod will fail to schedule.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-job
spec:
  tolerations:
    - key: nvidia.com/gpu
      operator: Exists
      effect: NoSchedule
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: cloud.google.com/gke-accelerator
              operator: In
              values:
                - nvidia-tesla-t4   # or nvidia-l4, nvidia-tesla-a100, etc.
  containers:
    - name: trainer
      image: nvcr.io/nvidia/pytorch:24.01-py3
      command: ["python", "train.py"]
      resources:
        limits:
          nvidia.com/gpu: "1"   # GPU in limits ONLY
      securityContext:
        allowPrivilegeEscalation: false
        runAsNonRoot: true
        runAsUser: 65532
        capabilities:
          drop: [ALL]
  restartPolicy: Never
```

## Time-Sharing (Software-Level GPU Sharing)

Time-sharing allows multiple pods to share a single GPU via software-level multiplexing. Not true hardware isolation -- pods contend for GPU time.

```bash
# Enable time-sharing on a node pool
gcloud container node-pools create shared-gpu-pool \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1,gpu-sharing-strategy=time-sharing,max-shared-clients-per-gpu=4 \
  --node-taints=nvidia.com/gpu=present:NoSchedule
```

Pods request fractional GPU implicitly -- each requests `nvidia.com/gpu: "1"` but the node allows up to `max-shared-clients-per-gpu` concurrent pods sharing that one GPU.

**When to use:** Multiple small inference services, development environments, batch jobs with low GPU utilization.

**When to avoid:** Training jobs that need full GPU bandwidth, latency-sensitive inference.

## MIG (Multi-Instance GPU)

MIG provides hardware partitioning at the GPU level. Supported on A100 and H100 only. Each MIG slice is an independent, isolated GPU partition with dedicated memory and compute.

- A100 40GB: up to 7 MIG slices (smallest: 1g.5gb = 1 GPU instance, 5 GB memory)
- A100 80GB: up to 7 MIG slices
- H100 80GB: up to 7 MIG slices

```bash
# Enable MIG on a node pool (A100 example)
gcloud container node-pools create mig-pool \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --machine-type=a2-highgpu-1g \
  --accelerator=type=nvidia-tesla-a100,count=1 \
  --node-taints=nvidia.com/gpu=present:NoSchedule
```

**Configure MIG profile via ConfigMap** (GPU Operator manages the rest):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: default-mig-parted-config
  namespace: gpu-operator
data:
  config.yaml: |
    version: v1
    mig-configs:
      all-1g.5gb:
        - devices: all
          mig-enabled: true
          mig-devices:
            "1g.5gb": 7
```

**Combining MIG + time-sharing:** Enable MIG first to partition the GPU hardware, then enable time-sharing on each MIG slice for additional software-level multiplexing.

```bash
--accelerator=type=nvidia-tesla-a100,count=1,gpu-sharing-strategy=time-sharing,max-shared-clients-per-gpu=2
```

## Node Auto-Provisioning (NAP) for GPU

NAP automatically creates GPU node pools when pods request GPU resources that no existing node pool satisfies.

```bash
# Enable NAP with GPU support
gcloud container clusters update CLUSTER_NAME \
  --region=REGION \
  --enable-autoprovisioning \
  --max-cpu=96 \
  --max-memory=624 \
  --autoprovisioning-resource-limits=nvidia.com/gpu=8
```

NAP reads pod `limits` (including `nvidia.com/gpu`) and creates a matching node pool automatically. The taint `nvidia.com/gpu=present:NoSchedule` is automatically applied to GPU node pools created by NAP.

## Spot GPU

Spot VMs offer 60-90% discount over on-demand for fault-tolerant GPU workloads (training with checkpointing, batch inference).

```bash
gcloud container node-pools create spot-gpu-pool \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --spot \
  --node-taints=nvidia.com/gpu=present:NoSchedule,cloud.google.com/gke-spot=true:NoSchedule \
  --enable-autoscaling \
  --min-nodes=0 \
  --max-nodes=20
```

Pod toleration for Spot:

```yaml
tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
  - key: cloud.google.com/gke-spot
    operator: Exists
    effect: NoSchedule
```

**Checkpointing is mandatory for Spot training jobs** -- Spot VMs can be preempted with 30-second notice. Use a persistent volume or Cloud Storage to save checkpoints periodically.

## TPU Basics

TPUs (Tensor Processing Units) are Google's custom ML accelerators, optimized for large transformer models.

```yaml
resources:
  limits:
    google.com/tpu: "4"   # Request 4 TPU chips (v4 pod = 4 chips)
```

**TPU topology selector:**

```yaml
nodeSelector:
  cloud.google.com/gke-tpu-topology: 2x2x1   # v4 TPU topology
  cloud.google.com/gke-tpu-accelerator: tpu-v4-podslice
```

**Autopilot TPU** (v1.29+): Autopilot supports TPU v4 and v5e. No driver management required.

**Standard TPU**: Requires dedicated TPU node pool with `--tpu-topology` flag.

```bash
gcloud container node-pools create tpu-pool \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --machine-type=ct4p-hightpu-4t \
  --tpu-topology=2x2x1 \
  --num-nodes=1
```

**Framework references for TPU workloads:**
- **vLLM**: High-throughput LLM serving, supports TPU v4/v5e
- **JetStream**: Google's high-performance inference framework for TPU
- **KubeRay**: Ray cluster operator for distributed training and inference (`helm install kuberay-operator kuberay/kuberay-operator`)

## Official References

- <https://cloud.google.com/kubernetes-engine/docs/how-to/gpus>
- <https://cloud.google.com/kubernetes-engine/docs/how-to/tpus>
- <https://cloud.google.com/kubernetes-engine/docs/concepts/gpu-time-sharing>
- <https://cloud.google.com/kubernetes-engine/docs/how-to/mig-configurations>
- <https://cloud.google.com/kubernetes-engine/docs/how-to/node-auto-provisioning>
