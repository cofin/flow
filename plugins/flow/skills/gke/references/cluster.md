# GKE Cluster Management

## Autopilot vs Standard Mode

### Autopilot (Recommended)

- Google manages nodes, scaling, security, upgrades.
- Pay per pod resource usage.
- Security best practices enforced by default.

```bash
gcloud container clusters create-auto CLUSTER_NAME \
  --region=REGION
```

### Standard Mode

- Full control over node configuration.
- Manual node pool management.
- Pay for node resources.

```bash
gcloud container clusters create CLUSTER_NAME \
  --region=REGION \
  --num-nodes=3 \
  --machine-type=e2-medium
```

---

## Cluster Creation Types

### Regional Cluster (Production)

Control plane replicated across zones for high availability.

```bash
gcloud container clusters create CLUSTER \
  --region=us-central1 \
  --num-nodes=2
```

### Private Cluster

Disables public IP addresses for nodes.

```bash
gcloud container clusters create CLUSTER \
  --region=us-central1 \
  --enable-private-nodes \
  --enable-private-endpoint \
  --master-ipv4-cidr=172.16.0.0/28 \
  --network=VPC_NAME \
  --subnetwork=SUBNET_NAME
```
