# Cloud Run Networking

## Multi-Container Services

Cloud Run supports sidecar containers for proxies, logging, etc.

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: multi-container-service
  annotations:
    run.googleapis.com/launch-stage: BETA
spec:
  template:
    metadata:
      annotations:
        # Container startup ordering
        run.googleapis.com/container-dependencies: "{nginx: [app]}"
    spec:
      containers:
        # Ingress container (receives traffic)
        - name: nginx
          image: nginx
          ports:
            - containerPort: 8080
          resources:
            limits:
              cpu: 500m
              memory: 256Mi
          startupProbe:
            tcpSocket:
              port: 8080
            timeoutSeconds: 240

        # Sidecar container
        - name: app
          image: my-app:latest
          env:
            - name: PORT
              value: "8888"
          resources:
            limits:
              cpu: 1000m
              memory: 512Mi
```

## Ingress Configuration

```bash
# Internal only (VPC)
gcloud run deploy SERVICE --ingress=internal

# Internal + Cloud Load Balancing
gcloud run deploy SERVICE --ingress=internal-and-cloud-load-balancing

# All traffic (public)
gcloud run deploy SERVICE --ingress=all
```

## VPC Connector

```bash
# Create connector
gcloud compute networks vpc-access connectors create CONNECTOR \
  --region=REGION \
  --network=VPC_NETWORK \
  --range=10.8.0.0/28

# Deploy with connector
gcloud run deploy SERVICE \
  --vpc-connector=CONNECTOR \
  --vpc-egress=all-traffic
```

## Secrets Management

```bash
# Use Secret Manager secret as env var
gcloud run deploy SERVICE \
  --set-secrets="DB_PASSWORD=db-password:latest"

# Mount secret as file
gcloud run deploy SERVICE \
  --set-secrets="/secrets/config.json=app-config:latest"
```
