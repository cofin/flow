# Identity-Aware Proxy (IAP) for Cloud Run

## Overview

Identity-Aware Proxy provides zero-trust access control for Cloud Run services. Users authenticate via their Google identity, and IAP forwards a signed JWT to the backend in the `X-Goog-IAP-JWT-Assertion` header. No login screen is needed -- users are authenticated seamlessly through Google Workspace.

- Official docs: <https://cloud.google.com/iap/docs/enabling-cloud-run>

## Authentication Flow

1. User requests the Cloud Run service URL.
2. IAP checks Google identity (redirects to login if unauthenticated).
3. IAP verifies the user has the `roles/iap.httpsResourceAccessor` role.
4. IAP forwards the request with the `X-Goog-IAP-JWT-Assertion` header.
5. The service validates the JWT signature against Google's JWKS endpoint.
6. The service extracts the user's email from the JWT claims.
7. The service looks up or auto-provisions the user in the database.

## IAP JWT Token

IAP sends a signed JWT (ES256 algorithm) in the `X-Goog-IAP-JWT-Assertion` header containing:

| Claim   | Description                                      |
|---------|--------------------------------------------------|
| `sub`   | Stable user identifier                           |
| `email` | User's email address                             |
| `azp`   | Authorized party (OAuth client ID)               |
| `aud`   | Expected audience (Cloud Run service path)       |
| `iss`   | Issuer: `https://cloud.google.com/iap`           |
| `exp`   | Token expiration                                 |
| `iat`   | Token issued at                                  |

Validate the JWT against Google's public JWKS keys at `https://www.gstatic.com/iap/verify/public_key-jwk`. Required validation checks: `exp`, `iat`, `aud`, `sub`, and `iss`.

## Environment Variables

| Variable                  | Example Value                                                  | Description                                 |
|---------------------------|----------------------------------------------------------------|---------------------------------------------|
| `AUTH_IAP_ENABLED`        | `true`                                                         | Enable IAP authentication                   |
| `IAP_AUDIENCE`            | `/projects/{PROJECT_NUM}/locations/{REGION}/services/{SERVICE}` | Auto-computed audience for JWT validation    |
| `AUTH_IAP_AUTO_PROVISION` | `true`                                                         | Auto-create users from IAP claims           |
| `AUTH_LOCAL_ENABLED`      | `false`                                                        | Disable local email/password login          |
| `IAP_ALLOWED_DOMAINS`     | `example.com,corp.example.com`                                 | Domain allowlist for auto-provisioning      |
| `IAP_CLOCK_SKEW_SECONDS`  | `30`                                                           | Clock skew tolerance for JWT validation     |

When `AUTH_IAP_ENABLED=true`, `IAP_AUDIENCE` is required. When both IAP and local auth are enabled a warning is emitted -- disable local auth in production to prevent bypass.

## User Auto-Provisioning

When `AUTH_IAP_AUTO_PROVISION=true`, first-time IAP users are created automatically:

1. JWT signature is validated against Google's public keys.
2. Email is extracted from the `email` claim.
3. If no matching user exists, a new account is created:
   - Email: from IAP token
   - Name: derived from email (prefix before `@`)
   - Verified: `true` (IAP handles verification)
   - Password: random (not used with IAP)

Use `IAP_ALLOWED_DOMAINS` to restrict which email domains can auto-provision. Without an allowlist, any authenticated Google account can create an account.

## Enabling IAP on Cloud Run

### Deploy with IAP enabled

```bash
gcloud run deploy SERVICE_NAME \
  --image=IMAGE_URL \
  --region=REGION \
  --project=PROJECT_ID \
  --ingress=all \
  --no-allow-unauthenticated \
  --iap
```

The `--iap` flag enables IAP on the Cloud Run service. Combined with `--no-allow-unauthenticated`, all traffic must pass through IAP.

### Enable the IAP API and service agent

```bash
# Enable IAP API
gcloud services enable iap.googleapis.com --project=PROJECT_ID

# Create IAP service identity
gcloud beta services identity create \
  --service=iap.googleapis.com \
  --project=PROJECT_ID
```

### Configure OAuth brand (consent screen)

```bash
# List existing brands
gcloud alpha iap oauth-brands list --project=PROJECT_ID --format=json

# Create brand if needed (Internal type for Workspace orgs)
gcloud alpha iap oauth-brands create \
  --project=PROJECT_ID \
  --application_title="My App" \
  --support_email="admin@example.com"
```

### Grant IAP service account run.invoker

The IAP service agent needs `roles/run.invoker` to forward requests to Cloud Run:

```bash
PROJECT_NUMBER=$(gcloud projects describe PROJECT_ID --format='value(projectNumber)')
IAP_SA="service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com"

gcloud run services add-iam-policy-binding SERVICE_NAME \
  --region=REGION \
  --member="serviceAccount:${IAP_SA}" \
  --role="roles/run.invoker"
```

### Grant user/group access

```bash
# Grant access to a Google Group
gcloud beta iap web add-iam-policy-binding \
  --project=PROJECT_ID \
  --resource-type=cloud-run \
  --service=SERVICE_NAME \
  --region=REGION \
  --member="group:team@example.com" \
  --role="roles/iap.httpsResourceAccessor"

# Grant access to an individual user
gcloud beta iap web add-iam-policy-binding \
  --project=PROJECT_ID \
  --resource-type=cloud-run \
  --service=SERVICE_NAME \
  --region=REGION \
  --member="user:alice@example.com" \
  --role="roles/iap.httpsResourceAccessor"

# Grant access to a service account (e.g., for Looker or programmatic access)
gcloud beta iap web add-iam-policy-binding \
  --project=PROJECT_ID \
  --resource-type=cloud-run \
  --service=SERVICE_NAME \
  --region=REGION \
  --member="serviceAccount:sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iap.httpsResourceAccessor"
```

## Terraform Configuration

```hcl
# Enable IAP API
resource "google_project_service" "iap" {
  project = var.project_id
  service = "iap.googleapis.com"
}

# Cloud Run service with IAP
resource "google_cloud_run_v2_service" "app" {
  name     = "my-service"
  location = var.region
  project  = var.project_id

  template {
    containers {
      image = var.image

      env {
        name  = "AUTH_IAP_ENABLED"
        value = "true"
      }
      env {
        name  = "IAP_AUDIENCE"
        value = "/projects/${data.google_project.project.number}/locations/${var.region}/services/my-service"
      }
      env {
        name  = "AUTH_IAP_AUTO_PROVISION"
        value = "true"
      }
      env {
        name  = "AUTH_LOCAL_ENABLED"
        value = "false"
      }
    }
  }
}

# IAP configuration for the Cloud Run service
resource "google_iap_web_type_compute_iam_member" "iap_access" {
  project = var.project_id
  role    = "roles/iap.httpsResourceAccessor"
  member  = "group:team@example.com"
}

# Grant IAP service agent run.invoker
resource "google_cloud_run_service_iam_member" "iap_invoker" {
  project  = var.project_id
  location = var.region
  service  = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-iap.iam.gserviceaccount.com"
}

# OAuth brand (consent screen)
resource "google_iap_brand" "project_brand" {
  project           = var.project_id
  support_email     = var.support_email
  application_title = "My App"
}
```

## Firewall Rules for IAP TCP Tunneling

For bastion hosts or debugging via IAP TCP tunneling, allow the IAP IP range:

```bash
gcloud compute firewall-rules create allow-iap-tcp \
  --project=PROJECT_ID \
  --network=VPC_NAME \
  --rules=tcp:22,tcp:5432,tcp:8888 \
  --source-ranges=35.235.240.0/20 \
  --description="Allow IAP TCP tunneling" \
  --direction=INGRESS \
  --action=ALLOW \
  --priority=1000 \
  --target-tags=bastion
```

Connect to a bastion through IAP:

```bash
gcloud compute ssh BASTION_NAME --zone=ZONE --tunnel-through-iap
```

## Security Considerations

- **Zero Trust**: Users must authenticate with Google AND have explicit IAP access via `roles/iap.httpsResourceAccessor`.
- **Disable local auth in production**: When IAP is enabled, set `AUTH_LOCAL_ENABLED=false` to prevent credential-based bypass.
- **Domain allowlist**: Use `IAP_ALLOWED_DOMAINS` to restrict auto-provisioning to specific email domains.
- **Audit logging**: All IAP access is logged in Cloud Logging.
- **Clock skew**: JWT validation allows configurable clock skew (default 30 seconds) for distributed systems.
