---
name: gke
description: "Auto-activate for kubectl commands, k8s/ directory, Helm charts. Kubernetes on GCP expertise for GKE. Produces Kubernetes deployments, Helm charts, and cluster configurations for GKE on GCP. Use when: running kubectl, Helm charts, pod/node pool management, workload identity, Kubernetes deployments, cluster scaling, or any GKE troubleshooting. Not for Cloud Run (see cloud-run), generic Kubernetes outside GCP, or local k8s (minikube/kind)."
---

# Google Kubernetes Engine (GKE)

GKE is Google Cloud's managed Kubernetes service, handling cluster management, upgrades, and scaling.

## Quick Reference

### kubectl Essentials

```bash
# Cluster access
gcloud container clusters get-credentials CLUSTER --region=REGION
kubectl config use-context CONTEXT_NAME

# Core operations
kubectl get nodes
kubectl get pods -A
kubectl logs -f POD_NAME -n NAMESPACE
kubectl exec -it POD_NAME -n NAMESPACE -- /bin/sh
kubectl apply -f manifest.yaml
```

### Deployment Workflow

1. **Cluster** -- Autopilot (recommended) or Standard mode, always regional for production.
2. **Workload Identity** -- bind KSA to GSA; never use node service accounts.
3. **Deploy** -- `kubectl apply` or Helm chart with per-component values (web, workers).
4. **Scale** -- HPA for pods, VPA for right-sizing, Cluster Autoscaler for nodes.
5. **Observe** -- `kubectl logs`, `kubectl describe`, `kubectl top`.

### Helm Chart Pattern

```text
chart/
  Chart.yaml
  values.yaml
  templates/
    _helpers.tpl
    web-deployment.yaml
    web-service.yaml
    worker-deployment.yaml
    migration-job.yaml
```

Structure `values.yaml` with separate sections per component (`web`, `workers`), each specifying `replicaCount`, `image`, `command`, `resources`, and `port`.

<workflow>

## Workflow

### Step 1: Cluster Setup

Choose Autopilot (Google-managed nodes, pay-per-pod) or Standard (full node control). Use regional clusters for production HA. Enable Workload Identity at cluster creation.

### Step 2: Workload Identity Configuration

```bash
# Create GSA + grant permissions
gcloud iam service-accounts create GSA_NAME
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:GSA_NAME@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Create KSA + bind to GSA
kubectl create serviceaccount KSA_NAME --namespace NAMESPACE
gcloud iam service-accounts add-iam-policy-binding \
  GSA_NAME@PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/KSA_NAME]"

# Annotate KSA
kubectl annotate serviceaccount KSA_NAME \
  --namespace=NAMESPACE \
  iam.gke.io/gcp-service-account=GSA_NAME@PROJECT_ID.iam.gserviceaccount.com
```

### Step 3: Deploy Application

Apply manifests or install Helm chart. Set resource requests/limits on every container. Add PodDisruptionBudgets for availability during upgrades.

### Step 4: Validate

Run `kubectl get pods -n NAMESPACE` to confirm healthy rollout. Check logs and events for errors.

</workflow>

<guardrails>

## Guardrails

- **Always use Workload Identity** -- never attach permissions via node service account. Bind KSA-to-GSA explicitly.
- **Set resource requests AND limits** on every container -- prevents noisy-neighbor issues and enables HPA/VPA.
- **Use PodDisruptionBudgets** -- ensures minimum availability during voluntary disruptions (node upgrades, cluster scaling).
- **Regional clusters for production** -- zonal clusters are single points of failure.
- **Autopilot preferred** unless you need GPU node pools or custom machine types.
- **Never expose workloads without network policies** -- restrict ingress/egress at the namespace level.

</guardrails>

<validation>

### Validation Checkpoint

Before delivering GKE configurations, verify:

- [ ] Workload Identity is configured (no node SA usage)
- [ ] Every container has resource requests and limits
- [ ] PodDisruptionBudgets are defined for production workloads
- [ ] Cluster is regional (not zonal) for production
- [ ] Health checks (readiness + liveness probes) are defined
- [ ] Namespace isolation and network policies are present

</validation>

<example>

## Example

**Task:** Deploy a web application with a Service on GKE.

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      serviceAccountName: web-app-ksa  # Workload Identity KSA
      containers:
        - name: web
          image: us-central1-docker.pkg.dev/my-project/repo/web-app:v1.2.0
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 1Gi
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 20
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: production
spec:
  selector:
    app: web-app
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP
---
# pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: production
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-app
```

</example>

---

## References Index

For detailed guides and configuration examples, refer to the following documents in `references/`:

- **[Cluster Management](references/cluster.md)** -- Autopilot vs Standard, Regional/Zonal setups, Private clusters.
- **[Node Pools](references/node_pools.md)** -- Creation, specialized pools (GPU, Spot), and management.
- **[Workload Identity](references/workload_identity.md)** -- Secure GCP API access configuration.
- **[Autoscaling](references/autoscaling.md)** -- HPA, VPA, and Cluster Autoscaler setups.
- **[Networking](references/networking.md)** -- Service types, GCE Ingress, and Network Policies.
- **[Security](references/security.md)** -- Hardening, Pod security contexts, and Secret Manager.
- **[Terraform Configuration](references/terraform.md)** -- Module examples for Autopilot and Standard.
- **[kubectl Commands](references/kubectl.md)** -- Essential access and operations commands.
- **[Troubleshooting](references/troubleshooting.md)** -- Debugging nodes, pods, and network issues.
- **[Helm Deployment](references/helm_deployment.md)** -- Helm chart patterns for web + worker deployments.
- **[SAQ Workers](references/saq_workers.md)** -- SAQ worker architecture, queue distribution, and graceful shutdown.

---

## Official References

- <https://cloud.google.com/kubernetes-engine/docs>
- <https://cloud.google.com/kubernetes-engine/docs/best-practices>
- <https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster>
