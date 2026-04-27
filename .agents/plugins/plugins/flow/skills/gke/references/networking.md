# GKE Networking

## Services

### ClusterIP (Internal)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: internal-service
spec:
  type: ClusterIP
  selector:
    app: my-app
  ports: [{ port: 80, targetPort: 8080 }]
```

### LoadBalancer (External)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: external-service
  annotations:
    cloud.google.com/neg: '{"ingress": true}'
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports: [{ port: 80, targetPort: 8080 }]
```

## Ingress (GCE)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    kubernetes.io/ingress.class: "gce"
    kubernetes.io/ingress.global-static-ip-name: "my-static-ip"
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service: { name: my-service, port: { number: 80 } }
```

## Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels: { app: backend }
  ingress:
  - from: [{ podSelector: { matchLabels: { app: frontend } } }]
```
