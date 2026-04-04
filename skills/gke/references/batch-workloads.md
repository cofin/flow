# Batch Workloads on GKE

Patterns for running batch Jobs, distributed training, and large GPU batch workloads on GKE.

## Kubernetes Job with GPU

A basic GPU training job. Use `restartPolicy: Never` for training (each failure creates a new pod); use `restartPolicy: OnFailure` only for idempotent tasks.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: gpu-training-job
spec:
  ttlSecondsAfterFinished: 3600   # auto-delete 1 hour after completion
  backoffLimit: 2                  # retry up to 2 times on failure
  template:
    spec:
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      nodeSelector:
        cloud.google.com/gke-accelerator: nvidia-tesla-a100
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      restartPolicy: Never
      containers:
        - name: trainer
          image: nvcr.io/nvidia/pytorch:24.01-py3
          command: ["python", "train.py", "--checkpoint-dir=/checkpoints"]
          resources:
            limits:
              nvidia.com/gpu: "1"   # GPU in limits ONLY
          volumeMounts:
            - name: checkpoints
              mountPath: /checkpoints
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
      volumes:
        - name: checkpoints
          persistentVolumeClaim:
            claimName: training-checkpoints-pvc
```

**Always use checkpointing for Spot GPU jobs.** Save checkpoints to a PVC or Cloud Storage (via GCS FUSE or `gsutil`) so training can resume after preemption.

## JobSet for Distributed Training

JobSet (v0.5+) is a Kubernetes API for coordinating multi-worker distributed training. Each `replicatedJob` represents a role (e.g., leader + workers). All jobs within a JobSet start and stop together.

```bash
# Install JobSet controller
kubectl apply --server-side -f https://github.com/kubernetes-sigs/jobset/releases/download/v0.5.1/manifests.yaml
```

```yaml
apiVersion: jobset.x-k8s.io/v1alpha2
kind: JobSet
metadata:
  name: distributed-training
spec:
  failurePolicy:
    maxRestarts: 3   # restart the entire JobSet up to 3 times on failure
  successPolicy:
    operator: All    # JobSet succeeds when all replicatedJobs complete
    targetReplicatedJobs:
      - workers
  replicatedJobs:
    - name: leader
      replicas: 1
      template:
        spec:
          backoffLimit: 0
          template:
            spec:
              tolerations:
                - key: nvidia.com/gpu
                  operator: Exists
                  effect: NoSchedule
              restartPolicy: Never
              containers:
                - name: leader
                  image: nvcr.io/nvidia/pytorch:24.01-py3
                  command: ["torchrun", "--nnodes=5", "--nproc_per_node=8", "--node_rank=0",
                            "--master_addr=$(JOBSET_NAME)-workers-0-0.$(JOBSET_NAME)",
                            "train.py"]
                  resources:
                    limits:
                      nvidia.com/gpu: "8"
                  env:
                    - name: JOBSET_NAME
                      valueFrom:
                        fieldRef:
                          fieldPath: metadata.labels['jobset.x-k8s.io/jobset-name']
    - name: workers
      replicas: 4   # 4 worker pods
      template:
        spec:
          backoffLimit: 0
          template:
            spec:
              tolerations:
                - key: nvidia.com/gpu
                  operator: Exists
                  effect: NoSchedule
              restartPolicy: Never
              containers:
                - name: worker
                  image: nvcr.io/nvidia/pytorch:24.01-py3
                  command: ["torchrun", "--nnodes=5", "--nproc_per_node=8",
                            "--node_rank=$(JOB_COMPLETION_INDEX)",
                            "--master_addr=$(JOBSET_NAME)-leader-0-0.$(JOBSET_NAME)",
                            "train.py"]
                  resources:
                    limits:
                      nvidia.com/gpu: "8"
```

JobSet creates headless Services for pod-to-pod communication. Pods address each other by DNS: `<jobset-name>-<replicatedjob-name>-<job-index>-<pod-index>.<jobset-name>`.

## ProvisioningRequest API (v1.28+)

ProvisioningRequest enables queued provisioning for large GPU batches. Instead of pods waiting in Pending state while node capacity is provisioned, submit a single request that GKE fulfills atomically before scheduling any pods.

**Best for:** Large A100/H100 training runs requiring 8+ GPU nodes that must all be available simultaneously.

```yaml
apiVersion: autoscaling.x-k8s.io/v1beta1
kind: ProvisioningRequest
metadata:
  name: large-training-run
spec:
  provisioningClassName: queued-provisioning.gke.io
  parameters:
    maxRunDurationSeconds: "86400"   # 24-hour max run duration
  podSets:
    - count: 8   # provision 8 nodes
      podTemplateRef:
        name: gpu-pod-template
---
apiVersion: v1
kind: PodTemplate
metadata:
  name: gpu-pod-template
template:
  spec:
    tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
    nodeSelector:
      cloud.google.com/gke-accelerator: nvidia-h100-80gb
    containers:
      - name: placeholder
        image: nvcr.io/nvidia/pytorch:24.01-py3
        resources:
          limits:
            nvidia.com/gpu: "8"
```

Monitor the ProvisioningRequest:

```bash
kubectl get provisioningrequest large-training-run -o yaml
kubectl describe provisioningrequest large-training-run
```

Once the request reaches `Provisioned` condition, submit the JobSet. GKE Cluster Autoscaler will place the pods on the pre-provisioned nodes.

**Flex-start provisioning** (alternative for fault-tolerant jobs): Uses `flex-start.gke.io` class. Provisions nodes as they become available rather than waiting for all at once -- better for training jobs with checkpointing.

```yaml
spec:
  provisioningClassName: flex-start.gke.io
```

## Cloud Batch vs GKE Jobs

Cloud Batch is a managed batch service that handles job scheduling, queueing, and VM lifecycle without Kubernetes. GKE Jobs run inside a Kubernetes cluster you manage (or Autopilot manages).

### When to use Cloud Batch

- Stateless batch jobs that don't need to communicate with other running services
- Simple GPU/CPU batch jobs without complex inter-pod communication
- No existing GKE cluster (avoid cluster overhead for pure batch)
- Need managed job queue with automatic retries, priority scheduling, and cost optimization
- Single-node GPU jobs without distributed training requirements

### When to use GKE Jobs

- Already running workloads in GKE (reuse existing cluster, Workload Identity, secrets)
- Distributed training requiring pod-to-pod networking (NCCL, Gloo)
- Need AlloyDB/Cloud SQL sidecar connectivity (Auth Proxy sidecar pattern)
- Complex orchestration: JobSets, initContainers, sidecars, custom volumes
- Jobs that interact with other GKE services (queuing, result storage, notifications)
- Need MIG or time-sharing GPU configurations

### Decision Table

| Factor | Cloud Batch | GKE Jobs |
|---|---|---|
| Existing GKE cluster | No | Yes |
| Distributed training (multi-node) | Limited | Yes (JobSet, MPI) |
| DB sidecar connectivity | No | Yes |
| Job queue management | Built-in | Custom (HPA + metrics) |
| Spot/preemptible support | Yes | Yes |
| Startup time | ~2 min (VM cold start) | Seconds (existing nodes) or minutes (new nodes) |
| Cost for infrequent jobs | Lower (no cluster) | Higher (cluster overhead) |
| GPU types | All | All |
| Cost visibility | Per-job billing | Cluster-level billing |

## Official References

- <https://cloud.google.com/kubernetes-engine/docs/how-to/batch/job>
- <https://cloud.google.com/kubernetes-engine/docs/concepts/jobset>
- <https://cloud.google.com/kubernetes-engine/docs/how-to/provisioningrequest>
- <https://cloud.google.com/batch/docs/get-started>
- <https://jobset.sigs.k8s.io/docs/>
