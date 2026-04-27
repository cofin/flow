# Cloud Run Terraform Configuration

## Basic Service

```hcl
resource "google_cloud_run_v2_service" "default" {
  name     = "my-service"
  location = "us-central1"

  template {
    containers {
      image = "gcr.io/my-project/my-image:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "ENV"
        value = "production"
      }

      # Secret from Secret Manager
      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/healthz"
        }
        initial_delay_seconds = 0
        timeout_seconds       = 1
        period_seconds        = 3
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/healthz"
        }
        period_seconds = 30
      }
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 100
    }

    max_instance_request_concurrency = 80
    timeout                          = "300s"
    service_account                  = google_service_account.run_sa.email
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}
```

## IAM Configuration

```hcl
# Public access
resource "google_cloud_run_service_iam_member" "public" {
  service  = google_cloud_run_v2_service.default.name
  location = google_cloud_run_v2_service.default.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Authenticated only
resource "google_cloud_run_service_iam_member" "auth" {
  service  = google_cloud_run_v2_service.default.name
  location = google_cloud_run_v2_service.default.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.invoker_sa}"
}
```

## Custom Domain

```hcl
resource "google_cloud_run_domain_mapping" "default" {
  location = "us-central1"
  name     = "api.example.com"

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = google_cloud_run_v2_service.default.name
  }
}
```
