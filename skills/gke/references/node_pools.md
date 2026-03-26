# GKE Node Pools

## Create Node Pool

```bash
gcloud container node-pools create POOL_NAME \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --machine-type=e2-standard-4 \
  --num-nodes=3 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10
```

## Specialized Pools

### GPU Node Pool

```bash
gcloud container node-pools create gpu-pool \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --machine-type=n1-standard-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --node-taints=nvidia.com/gpu=present:NoSchedule
```

### Spot VM Pool (Cost Savings)

```bash
gcloud container node-pools create spot-pool \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --spot \
  --machine-type=e2-standard-4
```

## Management Commands

```bash
# Resize
gcloud container clusters resize CLUSTER --node-pool=POOL --num-nodes=5 --region=REGION

# Update Autoscaling
gcloud container node-pools update POOL --cluster=CLUSTER --region=REGION --enable-autoscaling --min-nodes=1 --max-nodes=10
```
