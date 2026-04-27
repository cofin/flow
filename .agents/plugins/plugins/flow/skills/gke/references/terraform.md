# GKE Terraform Configuration

## Autopilot Cluster

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
}
```

## Standard Cluster with Node Pools

```hcl
module "gke" {
  source  = "terraform-google-modules/kubernetes-engine/google//modules/private-cluster"
  version = "~> 31.0"

  # ... network config ...

  node_pools = [
    {
      name         = "default-pool"
      machine_type = "e2-standard-4"
      min_count    = 1
      max_count    = 10
    },
    {
      name        = "spot-pool"
      machine_type = "e2-standard-4"
      spot        = true
    }
  ]
}
```
