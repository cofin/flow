# GKE Workload Identity

Workload Identity is the recommended way for GKE workloads to access Google Cloud APIs securely.

## 1. Enable on Cluster

```bash
# New cluster
gcloud container clusters create CLUSTER --workload-pool=PROJECT_ID.svc.id.goog

# Existing cluster
gcloud container clusters update CLUSTER --workload-pool=PROJECT_ID.svc.id.goog
```

## 2. Configure Binding

```bash
# Create Google Service Account (GSA)
gcloud iam service-accounts create GSA_NAME

# Grant GSA permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:GSA_NAME@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Create Kubernetes Service Account (KSA)
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

## 3. Pod Configuration

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  namespace: my-namespace
spec:
  serviceAccountName: my-ksa  # KSA with Workload Identity
```
