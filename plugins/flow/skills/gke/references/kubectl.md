# GKE kubectl Commands

## Cluster Access

```bash
# Get credentials
gcloud container clusters get-credentials CLUSTER --region=REGION

# Switch context
kubectl config use-context CONTEXT_NAME
```

## Common Operations

```bash
# Get nodes/pods
kubectl get nodes
kubectl get pods -A

# Logs
kubectl logs POD_NAME -n NAMESPACE
kubectl logs -f POD_NAME -n NAMESPACE  # follow

# Exec
kubectl exec -it POD_NAME -n NAMESPACE -- /bin/sh

# Apply
kubectl apply -f manifest.yaml
```
