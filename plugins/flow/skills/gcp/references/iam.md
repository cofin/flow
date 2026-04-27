# GCP IAM Reference

## Service Account Creation & Key Management

### Creating Service Accounts

```bash
# Create a service account
gcloud iam service-accounts create SA_NAME \
  --display-name="Human-readable name" \
  --description="Purpose of this account" \
  --project=PROJECT_ID

# List existing service accounts
gcloud iam service-accounts list --project=PROJECT_ID --format="json"
```

### Key Management

```bash
# Create a key (only when Workload Identity is not an option)
gcloud iam service-accounts keys create key.json \
  --iam-account=SA_NAME@PROJECT_ID.iam.gserviceaccount.com

# List keys for an account
gcloud iam service-accounts keys list \
  --iam-account=SA_NAME@PROJECT_ID.iam.gserviceaccount.com \
  --format="table(name, validAfterTime, validBeforeTime)"

# Delete a key
gcloud iam service-accounts keys delete KEY_ID \
  --iam-account=SA_NAME@PROJECT_ID.iam.gserviceaccount.com --quiet
```

## IAM Role Binding Patterns

### Project-Level Bindings

```bash
# Grant a role at the project level
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SA_NAME@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# Remove a role
gcloud projects remove-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SA_NAME@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# View current policy
gcloud projects get-iam-policy PROJECT_ID --format="json"
```

### Resource-Level Bindings

```bash
# Cloud Storage bucket
gcloud storage buckets add-iam-policy-binding gs://BUCKET_NAME \
  --member="serviceAccount:SA_NAME@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Cloud Run service
gcloud run services add-iam-policy-binding SERVICE_NAME \
  --region=REGION \
  --member="user:email@example.com" \
  --role="roles/run.invoker"

# Pub/Sub topic
gcloud pubsub topics add-iam-policy-binding TOPIC_NAME \
  --member="serviceAccount:SA_NAME@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"
```

### Conditional Bindings

```bash
# Grant access with a time-based condition
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:dev@example.com" \
  --role="roles/editor" \
  --condition="expression=request.time < timestamp('2026-06-01T00:00:00Z'),title=temp-access,description=Temporary editor access"
```

## Workload Identity

### GKE Workload Identity

Allows Kubernetes service accounts to act as IAM service accounts without keys.

```bash
# 1. Enable Workload Identity on the cluster
gcloud container clusters update CLUSTER_NAME \
  --region=REGION \
  --workload-pool=PROJECT_ID.svc.id.goog

# 2. Create a Kubernetes service account (via kubectl)
kubectl create serviceaccount KSA_NAME --namespace NAMESPACE

# 3. Create an IAM service account
gcloud iam service-accounts create GSA_NAME --project=PROJECT_ID

# 4. Grant the IAM SA the roles it needs
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:GSA_NAME@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# 5. Bind the KSA to the GSA
gcloud iam service-accounts add-iam-policy-binding \
  GSA_NAME@PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/KSA_NAME]"

# 6. Annotate the KSA
kubectl annotate serviceaccount KSA_NAME \
  --namespace NAMESPACE \
  iam.gke.io/gcp-service-account=GSA_NAME@PROJECT_ID.iam.gserviceaccount.com
```

### Cloud Run Workload Identity

Cloud Run uses the service account assigned at deploy time.

```bash
# Deploy with a specific service account
gcloud run deploy SERVICE_NAME \
  --image=IMAGE_URL \
  --region=REGION \
  --service-account=GSA_NAME@PROJECT_ID.iam.gserviceaccount.com

# Update an existing service's identity
gcloud run services update SERVICE_NAME \
  --region=REGION \
  --service-account=GSA_NAME@PROJECT_ID.iam.gserviceaccount.com
```

## Identity-Aware Proxy (IAP)

### Overview

Identity-Aware Proxy implements a zero-trust access model for GCP resources. Instead of relying on network perimeter security, IAP verifies user identity and context before granting access to applications. IAP sits in front of Cloud Run services, GKE ingresses, and Compute Engine instances, enforcing authentication and authorization at the infrastructure layer.

- Concepts: <https://cloud.google.com/iap/docs/concepts-overview>
- Enabling for Cloud Run: <https://cloud.google.com/iap/docs/enabling-cloud-run>

### IAP for Cloud Run

```bash
# Deploy with IAP enabled
gcloud run deploy SERVICE_NAME \
  --image=IMAGE_URL \
  --region=REGION \
  --no-allow-unauthenticated \
  --iap

# Enable IAP API
gcloud services enable iap.googleapis.com --project=PROJECT_ID

# Create IAP service identity
gcloud beta services identity create \
  --service=iap.googleapis.com \
  --project=PROJECT_ID

# Grant IAP service agent run.invoker so IAP can forward requests
PROJECT_NUMBER=$(gcloud projects describe PROJECT_ID --format='value(projectNumber)')
IAP_SA="service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com"

gcloud run services add-iam-policy-binding SERVICE_NAME \
  --region=REGION \
  --member="serviceAccount:${IAP_SA}" \
  --role="roles/run.invoker"
```

### IAP for GKE

```bash
# Enable IAP on a GKE backend service (via Ingress)
# IAP is configured through BackendConfig in GKE:
# 1. Create an OAuth client ID in the Cloud Console
# 2. Store client ID and secret in a Kubernetes secret
kubectl create secret generic iap-secret \
  --from-literal=client_id=CLIENT_ID \
  --from-literal=client_secret=CLIENT_SECRET

# 3. Reference in BackendConfig:
# apiVersion: cloud.google.com/v1
# kind: BackendConfig
# metadata:
#   name: iap-config
# spec:
#   iap:
#     enabled: true
#     oauthclientCredentials:
#       secretName: iap-secret
```

### Service Account Permissions for IAP

```bash
# IAP service agent needs run.invoker to forward requests to Cloud Run
gcloud run services add-iam-policy-binding SERVICE_NAME \
  --region=REGION \
  --member="serviceAccount:service-PROJECT_NUMBER@gcp-sa-iap.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Grant users/groups access through IAP
gcloud beta iap web add-iam-policy-binding \
  --project=PROJECT_ID \
  --resource-type=cloud-run \
  --service=SERVICE_NAME \
  --region=REGION \
  --member="group:team@example.com" \
  --role="roles/iap.httpsResourceAccessor"

# Grant IAP TCP tunneling access (for bastion/SSH)
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="group:devs@example.com" \
  --role="roles/iap.tunnelResourceAccessor"
```

### Key IAP Roles

| Role                              | Purpose                                          |
|-----------------------------------|--------------------------------------------------|
| `roles/iap.httpsResourceAccessor` | Access web applications behind IAP               |
| `roles/iap.tunnelResourceAccessor`| Access VMs via IAP TCP tunneling (SSH, RDP)      |
| `roles/iap.admin`                 | Full IAP configuration and policy management     |

### JWT Verification Patterns

IAP sends a signed JWT in the `X-Goog-IAP-JWT-Assertion` header. Backend services should validate this token to confirm the request came through IAP.

```bash
# JWT claims include: sub, email, aud, iss, exp, iat
# Issuer: https://cloud.google.com/iap
# Algorithm: ES256
# JWKS endpoint: https://www.gstatic.com/iap/verify/public_key-jwk
# Audience format for Cloud Run: /projects/{NUM}/locations/{REGION}/services/{SERVICE}
```

Validation checklist:

1. Verify signature against Google's JWKS public keys.
2. Check `iss` equals `https://cloud.google.com/iap`.
3. Check `aud` matches your service's expected audience.
4. Check `exp` has not passed (allow clock skew of ~30 seconds).
5. Extract `email` claim for user identification.

### OAuth Brand (Consent Screen)

```bash
# List existing brands
gcloud alpha iap oauth-brands list --project=PROJECT_ID --format=json

# Create internal brand for Workspace organizations
gcloud alpha iap oauth-brands create \
  --project=PROJECT_ID \
  --application_title="My App" \
  --support_email="admin@example.com"
```

## Best Practices

1. **Principle of least privilege**: Grant only the minimum roles required. Prefer predefined roles over primitive roles (`roles/viewer`, `roles/editor`, `roles/owner`).
2. **Avoid user-managed keys**: Use Workload Identity (GKE, Cloud Run) or default service account credentials wherever possible. Keys are long-lived secrets that are easy to leak.
3. **Rotate keys when unavoidable**: If you must use keys, rotate them regularly and delete old keys immediately.
4. **Use custom roles sparingly**: Prefer predefined roles. Create custom roles only when no predefined role matches the exact permission set needed.
5. **Audit regularly**: Use `gcloud asset search-all-iam-policies` or Policy Analyzer to review who has access to what.
6. **Scope service accounts per service**: Create dedicated service accounts for each workload rather than sharing a single account across services.
