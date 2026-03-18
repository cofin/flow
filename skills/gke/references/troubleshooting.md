# GKE Troubleshooting

## Node Issues

```bash
# Check node status and conditions
kubectl get nodes
kubectl describe node NODE_NAME

# Drain node for maintenance
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data
```

## Pod Issues

```bash
# Describe pod for events/errors
kubectl describe pod POD_NAME -n NAMESPACE

# Check events
kubectl get events -n NAMESPACE --sort-by='.lastTimestamp'

# Debug with ephemeral container
kubectl debug -it POD_NAME --image=busybox -n NAMESPACE
```

## Networking Issues

```bash
# Test DNS resolution
kubectl run -it --rm debug --image=busybox -- nslookup kubernetes

# Test service connectivity
kubectl run -it --rm debug --image=busybox -- wget -qO- http://service-name
```
