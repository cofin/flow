# GKE Autoscaling

## Horizontal Pod Autoscaler (HPA)

Scales replicas based on CPU/Memory.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-deployment
  minReplicas: 2
  maxReplicas: 100
  metrics:
  - type: Resource
    resource:
      name: cpu
      target: { type: Utilization, averageUtilization: 70 }
```

## Vertical Pod Autoscaler (VPA)

Adjusts CPU/Memory requests/limits for pods.

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-deployment
  updatePolicy:
    updateMode: "Auto"
```

## Cluster Autoscaler

Scales node pools up/down based on pod demand.

```bash
gcloud container clusters update CLUSTER \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=100 \
  --node-pool=POOL
```
