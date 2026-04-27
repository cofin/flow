# AlloyDB Omni Kubernetes Operator

## DBCluster CRD Spec

The `DBCluster` custom resource is the primary API object managed by the AlloyDB Omni operator.

**CRD group/version/kind:** `alloydbomni.dbadmin.goog/v1 / DBCluster`

### Full Field Reference

```yaml
apiVersion: alloydbomni.dbadmin.goog/v1
kind: DBCluster
metadata:
  name: <cluster-name>
  namespace: <namespace>
  annotations: {}           # operator-recognized annotations (e.g. backup trigger)
spec:
  databaseVersion: "15"     # PostgreSQL major version

  primarySpec:
    adminUser:
      passwordRef:
        name: <secret-name>  # Secret key: db-password
    resources:
      cpu: "4"               # vCPU request/limit
      memory: "16Gi"         # Memory request/limit
    parameters:              # PostgreSQL GUC overrides (ALTER SYSTEM equivalent)
      max_connections: "200"
      shared_buffers: "4GB"
      effective_cache_size: "12GB"
      work_mem: "64MB"
      maintenance_work_mem: "1GB"
      random_page_cost: "1.1"
      effective_io_concurrency: "200"
    availabilityOptions:
      livenessProbe: Enabled  # HTTP liveness check on the primary pod
      standby: Disabled       # Set to Enabled for HA automatic failover
    persistence:
      size: 100Gi
      storageClass: standard-rwo
      accessModes:
        - ReadWriteOnce

  readPoolSpec:               # Omit this section if read replicas are not needed
    replicas: 2
    resources:
      cpu: "2"
      memory: "8Gi"
    parameters:
      max_connections: "200"
    persistence:
      size: 100Gi
      storageClass: standard-rwo
```

### Secret for Admin Password

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: <secret-name>
  namespace: <namespace>
type: Opaque
stringData:
  db-password: <password>
```

---

## HA Failover Configuration

Enable automatic high availability by setting `standby: Enabled` in `availabilityOptions`. The operator provisions a synchronous standby pod in a different availability zone (when the cluster spans zones) and promotes it automatically if the primary becomes unavailable.

```yaml
apiVersion: alloydbomni.dbadmin.goog/v1
kind: DBCluster
metadata:
  name: ha-cluster
  namespace: database
spec:
  databaseVersion: "15"
  primarySpec:
    adminUser:
      passwordRef:
        name: db-password-secret
    resources:
      cpu: "4"
      memory: "16Gi"
    availabilityOptions:
      livenessProbe: Enabled
      standby: Enabled        # Activates automatic failover
    persistence:
      size: 200Gi
      storageClass: standard-rwo
  readPoolSpec:
    replicas: 2
    resources:
      cpu: "2"
      memory: "8Gi"
```

### Verifying HA Status

```bash
# Check cluster condition for HA readiness
kubectl get dbcluster ha-cluster -n database -o jsonpath='{.status.conditions}' | jq .

# Describe to see standby pod references and replication lag
kubectl describe dbcluster ha-cluster -n database

# Confirm both primary and standby pods are Running
kubectl get pods -n database -l dbcluster=ha-cluster
```

### Manual Failover Trigger (Testing)

```bash
# Delete the primary pod to trigger operator-managed promotion
kubectl delete pod ha-cluster-0 -n database

# Watch the operator promote the standby
kubectl get pods -n database -w
kubectl describe dbcluster ha-cluster -n database | grep -A5 "Conditions:"
```

---

## Scaling Read Replicas

Scale read replicas up or down with a single patch. The operator adds or removes replica pods without touching the primary.

```bash
# Scale to 3 read replicas
kubectl patch dbcluster <cluster-name> -n <namespace> \
    --type=merge \
    -p '{"spec":{"readPoolSpec":{"replicas":3}}}'

# Scale to 0 (remove all read replicas)
kubectl patch dbcluster <cluster-name> -n <namespace> \
    --type=merge \
    -p '{"spec":{"readPoolSpec":{"replicas":0}}}'

# Watch replica pod creation
kubectl get pods -n <namespace> -w

# Verify the read service endpoint is updated
kubectl get endpoints -n <namespace> | grep "\-ro"
```

### Read vs. Read-Write Services

The operator creates two Services automatically:

| Service suffix | Routes to | Use for |
|---|---|---|
| `-rw` | Primary only | All writes and read-after-write queries |
| `-ro` | Read replicas | Read-only analytical or reporting queries |

```bash
kubectl get svc -n <namespace>
# NAME                    TYPE        CLUSTER-IP    PORT(S)
# <cluster>-rw            ClusterIP   10.x.x.x      5432/TCP
# <cluster>-ro            ClusterIP   10.x.x.x      5432/TCP
```

---

## Rolling Update Patterns

### Parameter Updates (No Downtime)

Patching `primarySpec.parameters` causes the operator to apply parameters via `ALTER SYSTEM` and perform a coordinated rolling restart of the primary and replicas.

```bash
# Update max_connections (triggers rolling restart)
kubectl patch dbcluster <cluster-name> -n <namespace> \
    --type=merge \
    -p '{"spec":{"primarySpec":{"parameters":{"max_connections":"300","work_mem":"128MB"}}}}'

# Monitor the rolling restart
kubectl rollout status statefulset/<cluster-name> -n <namespace>
kubectl get pods -n <namespace> -w
```

### Resource Updates

```bash
# Increase CPU and memory
kubectl patch dbcluster <cluster-name> -n <namespace> \
    --type=merge \
    -p '{"spec":{"primarySpec":{"resources":{"cpu":"8","memory":"32Gi"}}}}'
```

### Monitoring Operator Reconciliation

```bash
# Stream operator logs during a change
kubectl logs -n alloydb-omni-system deployment/alloydb-omni-operator -f

# Check DBCluster conditions for reconciliation status
kubectl get dbcluster <cluster-name> -n <namespace> -o yaml | grep -A 20 "conditions:"
```

---

## Backup Annotation Patterns

The operator supports on-demand backup via an annotation. Backups are stored according to the backup configuration in the DBCluster spec (if configured) or the operator's default storage location.

```bash
# Trigger an immediate backup
kubectl annotate dbcluster <cluster-name> -n <namespace> \
    alloydbomni.dbadmin.goog/backup=true --overwrite

# List backup objects (if CRD is available)
kubectl get dbbackups -n <namespace>

# Describe a specific backup
kubectl describe dbbackup <backup-name> -n <namespace>
```

### Scheduled Backup Configuration

```yaml
spec:
  primarySpec:
    backupConfiguration:
      enabled: true
      schedule: "0 2 * * *"         # Daily at 02:00 UTC
      retainedBackups: 7             # Keep last 7 backups
      location: gs://<bucket>/backups  # GCS bucket or other configured backend
```

---

## Health Monitoring

### Readiness and Liveness Probes

The operator injects probes into the database pods automatically when `livenessProbe: Enabled` is set. For custom probe configuration via the underlying StatefulSet:

```bash
# Check probe status on the primary pod
kubectl describe pod <cluster-name>-0 -n <namespace> | grep -A 15 "Liveness:\|Readiness:"

# Check events for probe failures
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | grep -i "liveness\|readiness\|unhealthy"
```

### Cluster Health via pg_isready

```bash
# Direct readiness check via port-forward
kubectl port-forward svc/<cluster-name>-rw -n <namespace> 5432:5432 &
pg_isready -h localhost -U postgres
kill %1
```

### Operator-Level Health

```bash
# Check the operator deployment health
kubectl get deployment alloydb-omni-operator -n alloydb-omni-system
kubectl describe deployment alloydb-omni-operator -n alloydb-omni-system

# Check operator metrics (if metrics endpoint is exposed)
kubectl port-forward deployment/alloydb-omni-operator -n alloydb-omni-system 8080:8080 &
curl -s http://localhost:8080/metrics | grep dbcluster
```

### DBCluster Status Conditions

```bash
# Full status output
kubectl get dbcluster <cluster-name> -n <namespace> -o jsonpath='{.status}' | jq .

# Key conditions to check:
# Ready: True  — cluster is fully operational
# Reconciling: False — no pending changes
# Degraded: False — no pod failures
```

---

## Upgrade Procedures

### Minor Version / Image Tag Update

```bash
# Update the database version field (triggers rolling upgrade)
kubectl patch dbcluster <cluster-name> -n <namespace> \
    --type=merge \
    -p '{"spec":{"databaseVersion":"15.5"}}'

# Watch pods restart in order (replicas first, then primary)
kubectl get pods -n <namespace> -w

# Verify version after upgrade
kubectl port-forward svc/<cluster-name>-rw -n <namespace> 5432:5432 &
psql -h localhost -U postgres -c "SELECT version();"
```

### Operator Upgrade

```bash
# Apply the new operator manifest (replaces the existing operator deployment)
kubectl apply -f https://storage.googleapis.com/alloydb-omni-operator/<new-version>/alloydb-omni-operator.yaml

# Wait for the operator pod to roll over
kubectl rollout status deployment/alloydb-omni-operator -n alloydb-omni-system

# Confirm CRD schema was updated
kubectl get crd dbclusters.alloydbomni.dbadmin.goog -o jsonpath='{.spec.versions[*].name}'
```

### Pre-Upgrade Checklist

- [ ] Confirm current cluster status is `Ready` and not `Reconciling`
- [ ] Take a manual backup annotation before upgrading
- [ ] Review operator release notes for CRD schema changes
- [ ] Test the upgrade on a non-production cluster first
- [ ] Verify replication lag is 0 before upgrading the primary pod
