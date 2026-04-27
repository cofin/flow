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

## 4. Cloud Run to GKE Communication

When Cloud Run services need to communicate with GKE workloads (or vice versa), configure cross-service identity:

### Cloud Run Service Account Setup

```bash
# Create a dedicated GSA for the Cloud Run service
gcloud iam service-accounts create cloudrun-sa \
  --display-name="Cloud Run Service Account"

# Deploy Cloud Run with the GSA
gcloud run deploy SERVICE \
  --service-account=cloudrun-sa@PROJECT_ID.iam.gserviceaccount.com
```

### Grant Cloud Run Access to GKE Resources

```bash
# Allow Cloud Run's GSA to act as a GKE workload identity
gcloud iam service-accounts add-iam-policy-binding \
  GKE_GSA@PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.serviceAccountTokenCreator" \
  --member="serviceAccount:cloudrun-sa@PROJECT_ID.iam.gserviceaccount.com"

# Or grant specific roles directly
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:cloudrun-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/container.developer"
```

### Common IAM Roles for Cross-Service Access

| Role | Purpose |
|------|---------|
| `roles/iam.workloadIdentityUser` | Allow KSA to impersonate GSA |
| `roles/iam.serviceAccountTokenCreator` | Allow one GSA to create tokens for another |
| `roles/container.developer` | Access GKE resources (pods, services) |
| `roles/run.invoker` | Allow GKE workloads to invoke Cloud Run services |

## 5. Troubleshooting

```bash
# Verify Workload Identity binding
gcloud iam service-accounts get-iam-policy GSA_NAME@PROJECT_ID.iam.gserviceaccount.com

# Check KSA annotation
kubectl describe serviceaccount KSA_NAME -n NAMESPACE

# Test from a pod
kubectl run test-wi --image=google/cloud-sdk:slim --rm -it \
  --serviceaccount=KSA_NAME --namespace=NAMESPACE \
  -- gcloud auth list
```

## Official References

- <https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity>
- <https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity>
- <https://cloud.google.com/iam/docs/service-account-overview>
