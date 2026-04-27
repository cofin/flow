# Helm Deployment Patterns for Litestar Apps

Helm chart patterns for deploying Python ASGI applications (Litestar) with web servers and background workers on GKE.

## Chart Structure

```text
chart/
  Chart.yaml
  values.yaml
  templates/
    _helpers.tpl
    web-deployment.yaml
    web-service.yaml
    worker-deployment.yaml     # One per worker type or parameterized
    migration-job.yaml
    pvc.yaml                   # If using persistent storage
    configmap.yaml
    secrets.yaml
```

## Values Pattern: Per-Component Configuration

Structure values with separate sections for each component (web, workers, persistence):

```yaml
web:
  replicaCount: 2
  image:
    repository: us-central1-docker.pkg.dev/PROJECT/repo/app
    tag: latest
  port: 8080
  command: ["app", "server", "run", "--host", "0.0.0.0", "--port", "8080"]
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: "2"
      memory: 2Gi

workers:
  - name: default-worker
    replicaCount: 2
    concurrency: 4
    queues: ["default", "push", "ingress"]
    command: ["app", "server", "run-worker", "--queues", "default,push,ingress", "--concurrency", "4"]
    resources:
      requests:
        cpu: 250m
        memory: 256Mi
      limits:
        cpu: "1"
        memory: 1Gi

  - name: scheduler-worker
    replicaCount: 1        # Single replica only for scheduler queue
    concurrency: 1
    queues: ["scheduler"]
    command: ["app", "server", "run-worker", "--queues", "scheduler", "--concurrency", "1"]
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 512Mi

persistence:
  enabled: true
  storageClass: standard-rwo
  size: 10Gi
  accessMode: ReadWriteOnce
```

## Web Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-web
spec:
  replicas: {{ .Values.web.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}
      component: web
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
        component: web
    spec:
      serviceAccountName: {{ .Release.Name }}-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      containers:
        - name: web
          image: "{{ .Values.web.image.repository }}:{{ .Values.web.image.tag }}"
          command: {{ toJson .Values.web.command }}
          ports:
            - containerPort: {{ .Values.web.port }}
              protocol: TCP
          resources:
            {{- toYaml .Values.web.resources | nindent 12 }}
          startupProbe:
            httpGet:
              path: /health
              port: {{ .Values.web.port }}
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 30
          readinessProbe:
            httpGet:
              path: /health
              port: {{ .Values.web.port }}
            periodSeconds: 10
            failureThreshold: 3
          livenessProbe:
            tcpSocket:
              port: {{ .Values.web.port }}
            periodSeconds: 30
            failureThreshold: 5
      terminationGracePeriodSeconds: 30
```

## Worker Deployment

Template that iterates over worker definitions:

```yaml
{{- range .Values.workers }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ $.Release.Name }}-{{ .name }}
spec:
  replicas: {{ .replicaCount }}
  selector:
    matchLabels:
      app: {{ $.Release.Name }}
      component: {{ .name }}
  template:
    metadata:
      labels:
        app: {{ $.Release.Name }}
        component: {{ .name }}
    spec:
      serviceAccountName: {{ $.Release.Name }}-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      containers:
        - name: worker
          image: "{{ $.Values.web.image.repository }}:{{ $.Values.web.image.tag }}"
          command: {{ toJson .command }}
          resources:
            {{- toYaml .resources | nindent 12 }}
      terminationGracePeriodSeconds: 60
{{- end }}
```

## Health Probes

Use different probe types for different checks:

| Probe | Type | Target | Purpose |
|-------|------|--------|---------|
| **Startup** | HTTP GET | `/health` | Allow slow startup (e.g., DB migrations, model loading) |
| **Readiness** | HTTP GET | `/health` | Only receive traffic when healthy |
| **Liveness** | TCP Socket | Port | Restart if process is hung (avoids false positives from slow endpoints) |

Startup probes with high `failureThreshold` (e.g., 30 x 5s = 150s) give applications time to initialize without being killed.

## Database Migration Jobs

Run migrations as Kubernetes Jobs before or alongside deployment:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ .Release.Name }}-migrate-{{ .Release.Revision }}
  annotations:
    helm.sh/hook: pre-upgrade,pre-install
    helm.sh/hook-weight: "-5"
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  backoffLimit: 3
  template:
    spec:
      serviceAccountName: {{ .Release.Name }}-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
      containers:
        - name: migrate
          image: "{{ .Values.web.image.repository }}:{{ .Values.web.image.tag }}"
          command: ["app", "manage", "upgrade-database"]
          envFrom:
            - secretRef:
                name: {{ .Release.Name }}-secrets
      restartPolicy: Never
```

## Persistence with Pod Affinity

When using `ReadWriteOnce` PVCs, pods must be scheduled on the same node:

```yaml
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchExpressions:
              - key: app
                operator: In
                values:
                  - {{ .Release.Name }}
          topologyKey: kubernetes.io/hostname
```

## Security Context

Always apply security contexts at both pod and container levels:

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    fsGroup: 65532
  containers:
    - name: app
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
```

## Official References

- <https://helm.sh/docs/>
- <https://kubernetes.io/docs/concepts/workloads/>
- <https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/>
- <https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/>
