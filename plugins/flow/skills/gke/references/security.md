# GKE Security

## Cluster Hardening

```bash
# Enable Shielded Nodes
gcloud container clusters create CLUSTER \
  --enable-shielded-nodes \
  --shielded-secure-boot

# Enable Binary Authorization
gcloud container clusters update CLUSTER --enable-binauthz
```

## Pod Security Context

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile: { type: RuntimeDefault }
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities: { drop: [ALL] }
```

## Secret Manager Integration

```bash
# Enable Secret Manager add-on
gcloud container clusters update CLUSTER --enable-secret-manager
```

```yaml
# Mount secrets via CSI
spec:
  volumes:
  - name: secrets
    csi:
      driver: secrets-store.csi.k8s.io
      volumeAttributes: { secretProviderClass: "gcp-secrets" }
```
