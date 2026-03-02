---
name: gke
description: Expert knowledge for Google Kubernetes Engine (GKE). Use when creating clusters, managing node pools, configuring workloads, setting up security with Workload Identity, or troubleshooting GKE deployments.
---

# Google Kubernetes Engine (GKE) Skill

## Scope

Use this skill when working with GKE cluster design, lifecycle operations, security, and networking decisions.

## Fast Decision Guide

- Prefer `Autopilot` for most new workloads and teams that want less node-level operational overhead.
- Use `Standard` when you need deep node control, custom node pools, or specialized scheduling setup.
- Prefer `regional` clusters for production control plane resilience.
- Enroll in a release channel. `Regular` is usually the best default.

## Current Platform Notes

- GKE supports both full Autopilot clusters and Autopilot mode workloads in Standard clusters.
- Release channels include `Rapid`, `Regular` (recommended default), `Stable`, and `Extended` (long-term support).
- For GKE Ingress, GKE still requires the `kubernetes.io/ingress.class` annotation (`gce` / `gce-internal`); `spec.ingressClassName` is not used for GKE Ingress.
- Prefer the term `Workload Identity Federation for GKE` (formerly commonly called Workload Identity).

## Cluster Creation Baselines

### Autopilot

```bash
gcloud container clusters create-auto CLUSTER_NAME \
  --location=us-central1 \
  --release-channel=regular
```

### Standard (regional, production-oriented baseline)

```bash
gcloud container clusters create CLUSTER_NAME \
  --location=us-central1 \
  --release-channel=regular \
  --enable-ip-alias \
  --workload-pool=PROJECT_ID.svc.id.goog \
  --enable-private-nodes \
  --enable-shielded-nodes \
  --enable-dataplane-v2
```

### Get kubeconfig credentials

```bash
gcloud container clusters get-credentials CLUSTER_NAME --location=us-central1
```

## Node Pool Operations (Standard)

### Create autoscaled pool

```bash
gcloud container node-pools create app-pool \
  --cluster=CLUSTER_NAME \
  --location=us-central1 \
  --machine-type=e2-standard-4 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10 \
  --disk-size=100 \
  --disk-type=pd-balanced
```

### Create Spot pool

```bash
gcloud container node-pools create spot-pool \
  --cluster=CLUSTER_NAME \
  --location=us-central1 \
  --spot \
  --machine-type=e2-standard-4 \
  --enable-autoscaling \
  --min-nodes=0 \
  --max-nodes=20
```

### Enable autoscaling on an existing pool

```bash
gcloud container clusters update CLUSTER_NAME \
  --location=us-central1 \
  --node-pool=POOL_NAME \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10
```

## Identity and Access

Prefer Workload Identity Federation for GKE over service account keys.

### Enable on Standard cluster

```bash
gcloud container clusters update CLUSTER_NAME \
  --location=us-central1 \
  --workload-pool=PROJECT_ID.svc.id.goog
```

### Ensure node pool uses GKE metadata server

```bash
gcloud container node-pools update POOL_NAME \
  --cluster=CLUSTER_NAME \
  --location=us-central1 \
  --workload-metadata=GKE_METADATA
```

## Autoscaling

- Use HPA for replica count scaling based on workload metrics.
- Use Cluster Autoscaler for node count scaling.
- Consider Node Auto-Provisioning when node shape requirements vary significantly.

## Networking Guidance

- Use Gateway API for modern L7 patterns where supported by your platform architecture.
- Use GKE Ingress when you need the managed external/internal Application Load Balancer controller behavior tied to classic Ingress semantics.
- If using network policies with Workload Identity Federation for GKE, allow metadata server egress per official guidance.

## Security Checklist

- Use private nodes for production where possible.
- Use Workload Identity Federation for GKE.
- Use Shielded GKE Nodes.
- Use GKE Dataplane V2 unless a specific incompatibility blocks it.
- Enforce Pod-level least privilege (`runAsNonRoot`, drop Linux capabilities, `seccompProfile`).
- Store secrets in Secret Manager and mount via the Secret Manager add-on / CSI integration.

## Troubleshooting Quick Commands

```bash
kubectl get nodes
kubectl get pods -A
kubectl describe pod POD_NAME -n NAMESPACE
kubectl get events -n NAMESPACE --sort-by='.lastTimestamp'
kubectl logs POD_NAME -n NAMESPACE
kubectl logs -f POD_NAME -n NAMESPACE
kubectl debug -it POD_NAME --image=busybox -n NAMESPACE
```

## Learn More (Official)

- GKE docs hub: https://cloud.google.com/kubernetes-engine/docs
- Autopilot overview: https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview
- Release channels: https://cloud.google.com/kubernetes-engine/docs/concepts/release-channels
- Workload Identity Federation for GKE: https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity
- GKE Ingress concepts: https://cloud.google.com/kubernetes-engine/docs/concepts/ingress
- Gateway API on GKE: https://cloud.google.com/kubernetes-engine/docs/concepts/gateway-api
- Cluster autoscaler: https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-autoscaler
- Dataplane V2: https://cloud.google.com/kubernetes-engine/docs/how-to/dataplane-v2
- Network policy: https://cloud.google.com/kubernetes-engine/docs/how-to/network-policy
- Secret Manager add-on for GKE: https://cloud.google.com/secret-manager/docs/secret-manager-managed-csi-component
- gcloud GKE cluster commands: https://cloud.google.com/sdk/gcloud/reference/container/clusters
- gcloud GKE node pool commands: https://cloud.google.com/sdk/gcloud/reference/container/node-pools/create
- GKE release notes: https://cloud.google.com/kubernetes-engine/docs/release-notes
- Kubernetes upstream docs: https://kubernetes.io/docs/home/

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [GCP Scripting](https://github.com/cofin/flow/blob/main/templates/styleguides/cloud/gcp_scripting.md)
- [Bash](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/bash.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
