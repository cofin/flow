---
name: gke
description: Expert knowledge for Google Kubernetes Engine (GKE). Use when creating clusters, managing node pools, configuring workloads, setting up security, or troubleshooting deployments.
---

# Google Kubernetes Engine (GKE)

## Overview

GKE is Google Cloud's managed Kubernetes service, handling cluster management, upgrades, and scaling.

---

## References Index

For detailed guides and configuration examples, refer to the following documents in `references/`:

- **[Cluster Management](references/cluster.md)**
  - Autopilot vs Standard, Regional/Zonal setups, Private clusters.
- **[Node Pools](references/node_pools.md)**
  - Creation, specialized pools (GPU, Spot), and management.
- **[Workload Identity](references/workload_identity.md)**
  - Secure GCP API access configuration.
- **[Autoscaling](references/autoscaling.md)**
  - HPA, VPA, and Cluster Autoscaler setups.
- **[Networking](references/networking.md)**
  - Service types, GCE Ingress, and Network Policies.
- **[Security](references/security.md)**
  - Hardening, Pod security contexts, and Secret Manager.
- **[Terraform Configuration](references/terraform.md)**
  - Module examples for Autopilot and Standard.
- **[kubectl Commands](references/kubectl.md)**
  - Essential access and operations commands.
- **[Troubleshooting](references/troubleshooting.md)**
  - Debugging nodes, pods, and network issues.

---

## Official References

- https://cloud.google.com/kubernetes-engine/docs
- https://cloud.google.com/kubernetes-engine/docs/best-practices
- https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster
