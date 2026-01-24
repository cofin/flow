---
name: gke
description: Expert knowledge for Google Kubernetes Engine (GKE). Use when creating clusters, managing node pools, configuring workloads, setting up security with Workload Identity, or troubleshooting GKE deployments.
---

# Google Kubernetes Engine (GKE) Skill

## Overview

GKE is Google Cloud's managed Kubernetes service. It handles cluster management, upgrades, scaling, and integrates deeply with Google Cloud services.

## Autopilot vs Standard Mode

### Autopilot (Recommended for most workloads)

- Google manages nodes, scaling, security, upgrades
- Pay per pod resource usage
- Security best practices enforced by default
- Simplified operations

```bash
gcloud container clusters create-auto CLUSTER_NAME \
  --region=REGION \
  --project=PROJECT_ID
```

### Standard Mode

- Full control over node configuration
- Manual node pool management
- More flexibility, more responsibility
- Pay for node resources (used or not)

```bash
gcloud container clusters create CLUSTER_NAME \
  --region=REGION \
  --num-nodes=3 \
  --machine-type=e2-medium
```

### Feature Comparison

| Feature | Autopilot | Standard |
|---------|-----------|----------|
| Node management | Automatic | Manual |
| Security hardening | Enforced | Optional |
| Workload Identity | Always on | Must enable |
| Node pool customization | Limited | Full control |
| GPU/TPU support | Yes | Yes |
| Pricing model | Per pod | Per node |

## Cluster Creation

### Regional vs Zonal

**Regional (Production)**: Control plane replicated across zones
```bash
gcloud container clusters create CLUSTER \
  --region=us-central1 \
  --num-nodes=2
```

**Zonal (Development)**: Single zone, lower cost
```bash
gcloud container clusters create CLUSTER \
  --zone=us-central1-a \
  --num-nodes=3
```

### Private Cluster

```bash
gcloud container clusters create CLUSTER \
  --region=us-central1 \
  --enable-private-nodes \
  --enable-private-endpoint \
  --master-ipv4-cidr=172.16.0.0/28 \
  --network=VPC_NAME \
  --subnetwork=SUBNET_NAME \
  --cluster-secondary-range-name=pods \
  --services-secondary-range-name=services
```

### Full Production Cluster

```bash
gcloud container clusters create production-cluster \
  --region=us-central1 \
  --release-channel=regular \
  --enable-ip-alias \
  --enable-private-nodes \
  --master-ipv4-cidr=172.16.0.0/28 \
  --network=production-vpc \
  --subnetwork=gke-subnet \
  --workload-pool=PROJECT_ID.svc.id.goog \
  --enable-shielded-nodes \
  --shielded-secure-boot \
  --enable-dataplane-v2 \
  --logging=SYSTEM,WORKLOAD \
  --monitoring=SYSTEM,WORKLOAD \
  --addons=HttpLoadBalancing,HorizontalPodAutoscaling,GcePersistentDiskCsiDriver
```

## Node Pools

### Create Node Pool

```bash
gcloud container node-pools create POOL_NAME \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --machine-type=e2-standard-4 \
  --num-nodes=3 \
  --min-nodes=1 \
  --max-nodes=10 \
  --enable-autoscaling \
  --disk-size=100GB \
  --disk-type=pd-ssd \
  --image-type=COS_CONTAINERD \
  --service-account=SA@PROJECT.iam.gserviceaccount.com
```

### GPU Node Pool

```bash
gcloud container node-pools create gpu-pool \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --machine-type=n1-standard-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --num-nodes=0 \
  --min-nodes=0 \
  --max-nodes=5 \
  --enable-autoscaling \
  --node-taints=nvidia.com/gpu=present:NoSchedule
```

### Spot/Preemptible Node Pool (Cost Savings)

```bash
gcloud container node-pools create spot-pool \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --spot \
  --machine-type=e2-standard-4 \
  --num-nodes=0 \
  --min-nodes=0 \
  --max-nodes=20 \
  --enable-autoscaling
```

### Node Pool Management

```bash
# List node pools
gcloud container node-pools list --cluster=CLUSTER --region=REGION

# Resize node pool
gcloud container clusters resize CLUSTER \
  --node-pool=POOL \
  --num-nodes=5 \
  --region=REGION

# Update node pool
gcloud container node-pools update POOL \
  --cluster=CLUSTER \
  --region=REGION \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10

# Delete node pool
gcloud container node-pools delete POOL --cluster=CLUSTER --region=REGION
```

## Workload Identity

Workload Identity is the recommended way for GKE workloads to access Google Cloud APIs.

### Enable on Cluster

```bash
# New cluster
gcloud container clusters create CLUSTER \
  --workload-pool=PROJECT_ID.svc.id.goog

# Existing cluster
gcloud container clusters update CLUSTER \
  --workload-pool=PROJECT_ID.svc.id.goog
```

### Enable on Node Pool

```bash
gcloud container node-pools update POOL \
  --cluster=CLUSTER \
  --workload-metadata=GKE_METADATA
```

### Configure Workload Identity

```bash
# Create Google Service Account
gcloud iam service-accounts create GSA_NAME

# Grant permissions to GSA
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:GSA_NAME@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Create Kubernetes Service Account
kubectl create serviceaccount KSA_NAME --namespace NAMESPACE

# Bind KSA to GSA
gcloud iam service-accounts add-iam-policy-binding \
  GSA_NAME@PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/KSA_NAME]"

# Annotate KSA
kubectl annotate serviceaccount KSA_NAME \
  --namespace=NAMESPACE \
  iam.gke.io/gcp-service-account=GSA_NAME@PROJECT_ID.iam.gserviceaccount.com
```

### Pod Configuration

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  namespace: my-namespace
spec:
  serviceAccountName: my-ksa  # KSA with Workload Identity
  containers:
  - name: app
    image: my-image
```

## Autoscaling

### Horizontal Pod Autoscaler (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-deployment
  minReplicas: 2
  maxReplicas: 100
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
```

### Vertical Pod Autoscaler (VPA)

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-deployment
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: "*"
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 4
        memory: 8Gi
```

### Cluster Autoscaler

```bash
# Enable on node pool
gcloud container clusters update CLUSTER \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=100 \
  --node-pool=POOL

# Node Auto-Provisioning (NAP)
gcloud container clusters update CLUSTER \
  --enable-autoprovisioning \
  --min-cpu=1 \
  --max-cpu=100 \
  --min-memory=1 \
  --max-memory=400
```

## Networking

### Services

```yaml
# ClusterIP (internal)
apiVersion: v1
kind: Service
metadata:
  name: internal-service
spec:
  type: ClusterIP
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080

---
# LoadBalancer (external)
apiVersion: v1
kind: Service
metadata:
  name: external-service
  annotations:
    cloud.google.com/neg: '{"ingress": true}'
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```

### Ingress with Google Cloud Load Balancer

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    kubernetes.io/ingress.class: "gce"
    kubernetes.io/ingress.global-static-ip-name: "my-static-ip"
    networking.gke.io/managed-certificates: "my-cert"
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: my-service
            port:
              number: 80
```

### Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress

---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - port: 8080
```

## Security Best Practices

### Cluster Hardening

```bash
# Enable Shielded GKE Nodes
gcloud container clusters create CLUSTER \
  --enable-shielded-nodes \
  --shielded-secure-boot \
  --shielded-integrity-monitoring

# Enable Binary Authorization
gcloud container clusters update CLUSTER \
  --enable-binauthz

# Disable legacy APIs
gcloud container clusters update CLUSTER \
  --no-enable-legacy-abac
```

### Pod Security

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: my-image
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
    resources:
      limits:
        cpu: "1"
        memory: "1Gi"
      requests:
        cpu: "100m"
        memory: "128Mi"
```

### Secret Management

```bash
# Enable Secret Manager add-on
gcloud container clusters update CLUSTER \
  --enable-secret-manager

# Use secrets in pods via CSI driver
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-secrets
spec:
  serviceAccountName: my-ksa
  containers:
  - name: app
    image: my-image
    volumeMounts:
    - name: secrets
      mountPath: "/etc/secrets"
      readOnly: true
  volumes:
  - name: secrets
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: "gcp-secrets"
```

## Terraform Configuration

### Autopilot Cluster

```hcl
module "gke_autopilot" {
  source  = "terraform-google-modules/kubernetes-engine/google//modules/beta-autopilot-private-cluster"
  version = "~> 31.0"

  project_id        = var.project_id
  name              = "autopilot-cluster"
  region            = "us-central1"
  network           = google_compute_network.vpc.name
  subnetwork        = google_compute_subnetwork.subnet.name
  ip_range_pods     = "pods"
  ip_range_services = "services"

  enable_private_endpoint = false
  enable_private_nodes    = true
  master_ipv4_cidr_block  = "172.16.0.0/28"

  release_channel = "REGULAR"
}
```

### Standard Cluster with Node Pools

```hcl
module "gke" {
  source  = "terraform-google-modules/kubernetes-engine/google//modules/private-cluster"
  version = "~> 31.0"

  project_id = var.project_id
  name       = "standard-cluster"
  region     = "us-central1"
  zones      = ["us-central1-a", "us-central1-b", "us-central1-f"]

  network           = google_compute_network.vpc.name
  subnetwork        = google_compute_subnetwork.subnet.name
  ip_range_pods     = "pods"
  ip_range_services = "services"

  enable_private_endpoint    = false
  enable_private_nodes       = true
  master_ipv4_cidr_block     = "172.16.0.0/28"

  # Workload Identity
  identity_namespace = "${var.project_id}.svc.id.goog"

  # Security
  enable_shielded_nodes = true

  release_channel = "REGULAR"

  node_pools = [
    {
      name               = "default-pool"
      machine_type       = "e2-standard-4"
      min_count          = 1
      max_count          = 10
      disk_size_gb       = 100
      disk_type          = "pd-ssd"
      image_type         = "COS_CONTAINERD"
      auto_repair        = true
      auto_upgrade       = true
      preemptible        = false
      initial_node_count = 3
    },
    {
      name               = "spot-pool"
      machine_type       = "e2-standard-4"
      min_count          = 0
      max_count          = 20
      disk_size_gb       = 100
      spot               = true
      auto_repair        = true
      auto_upgrade       = true
      initial_node_count = 0
    }
  ]

  node_pools_oauth_scopes = {
    all = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
  }

  node_pools_labels = {
    all           = {}
    default-pool  = { environment = "production" }
    spot-pool     = { environment = "production", preemptible = "true" }
  }

  node_pools_taints = {
    all       = []
    spot-pool = [
      {
        key    = "preemptible"
        value  = "true"
        effect = "NO_SCHEDULE"
      }
    ]
  }
}
```

## kubectl Commands

### Cluster Access

```bash
# Get credentials
gcloud container clusters get-credentials CLUSTER --region=REGION

# View config
kubectl config view
kubectl config current-context

# Switch context
kubectl config use-context CONTEXT_NAME
```

### Common Operations

```bash
# Get resources
kubectl get nodes
kubectl get pods -A
kubectl get services -A
kubectl get deployments -n NAMESPACE

# Describe resources
kubectl describe node NODE_NAME
kubectl describe pod POD_NAME -n NAMESPACE

# Logs
kubectl logs POD_NAME -n NAMESPACE
kubectl logs -f POD_NAME -n NAMESPACE  # follow
kubectl logs POD_NAME -c CONTAINER -n NAMESPACE  # specific container

# Exec into pod
kubectl exec -it POD_NAME -n NAMESPACE -- /bin/sh

# Port forward
kubectl port-forward svc/SERVICE 8080:80 -n NAMESPACE

# Apply manifests
kubectl apply -f manifest.yaml
kubectl apply -k ./kustomization/

# Delete resources
kubectl delete -f manifest.yaml
kubectl delete pod POD_NAME -n NAMESPACE
```

## Release Channels

| Channel | Description | Use Case |
|---------|-------------|----------|
| Rapid | Newest features | Testing new features |
| Regular | Balance of features/stability | Most production |
| Stable | Maximum stability | Critical workloads |

```bash
# Set release channel
gcloud container clusters create CLUSTER --release-channel=regular

# Update release channel
gcloud container clusters update CLUSTER --release-channel=stable
```

## Troubleshooting

### Node Issues

```bash
# Check node status
kubectl get nodes
kubectl describe node NODE_NAME

# Drain node for maintenance
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data

# Uncordon node
kubectl uncordon NODE_NAME
```

### Pod Issues

```bash
# Check pod status
kubectl get pods -n NAMESPACE
kubectl describe pod POD_NAME -n NAMESPACE

# Check events
kubectl get events -n NAMESPACE --sort-by='.lastTimestamp'

# Debug with ephemeral container
kubectl debug -it POD_NAME --image=busybox -n NAMESPACE
```

### Networking Issues

```bash
# Test DNS
kubectl run -it --rm debug --image=busybox -- nslookup kubernetes

# Test connectivity
kubectl run -it --rm debug --image=busybox -- wget -qO- http://service-name

# Check network policies
kubectl get networkpolicies -A
```

## Best Practices Summary

### Operations
1. Use **Autopilot** for most workloads
2. Enable **release channels** for automated upgrades
3. Use **regional clusters** for production
4. Enable **node auto-repair and auto-upgrade**

### Security
1. Enable **Workload Identity** for all clusters
2. Use **private clusters** with authorized networks
3. Enable **Shielded GKE Nodes**
4. Apply **Pod Security Standards**
5. Use **Secret Manager** instead of Kubernetes secrets

### Cost Optimization
1. Use **Spot VMs** for fault-tolerant workloads
2. Enable **cluster autoscaler** and **VPA**
3. Right-size node pools
4. Use **Autopilot** for automatic optimization

### Reliability
1. Use **Pod Disruption Budgets**
2. Configure **resource requests and limits**
3. Use **anti-affinity rules** for HA
4. Enable **monitoring and logging**

## Resources

- [GKE Documentation](https://cloud.google.com/kubernetes-engine/docs)
- [GKE Best Practices](https://cloud.google.com/kubernetes-engine/docs/best-practices)
- [Hardening Guide](https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster)
- [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [Autopilot Overview](https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview)
