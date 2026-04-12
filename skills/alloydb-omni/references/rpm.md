# RPM Deployment

## Use When

Use the RPM path for:

- RHEL, Rocky Linux, AlmaLinux, CentOS Stream, or Oracle Linux hosts
- VM and bare-metal deployments without container orchestration
- Environments where `systemd` lifecycle management is preferred over Docker or Kubernetes

## Install

```bash
sudo tee /etc/yum.repos.d/alloydb-omni.repo << 'EOF'
[alloydb-omni]
name=AlloyDB Omni
baseurl=https://storage.googleapis.com/alloydb-omni-yum/
enabled=1
gpgcheck=0
EOF

sudo yum install -y alloydbomni
```

## Initialize

```bash
sudo mkdir -p /var/lib/alloydb/data
sudo alloydb-omni init --data-dir=/var/lib/alloydb/data
```

## Service Lifecycle

```bash
sudo systemctl enable --now alloydb-omni
sudo systemctl status alloydb-omni
sudo journalctl -u alloydb-omni -f
```

## Post-Install Configuration

Primary config file:

```text
/var/lib/alloydb/data/postgresql.conf
```

Recommended first-pass tuning:

```bash
sudo -u postgres psql -c "ALTER SYSTEM SET shared_buffers = '4GB';"
sudo -u postgres psql -c "ALTER SYSTEM SET effective_cache_size = '12GB';"
sudo -u postgres psql -c "ALTER SYSTEM SET work_mem = '64MB';"
sudo -u postgres psql -c "ALTER SYSTEM SET maintenance_work_mem = '1GB';"
sudo systemctl restart alloydb-omni
```

Enable key extensions after restart:

```bash
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS google_columnar_engine;"
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## Validation

```bash
psql -h localhost -U postgres -c "SELECT version();"
sudo systemctl is-active alloydb-omni
sudo -u postgres psql -c "SELECT extname FROM pg_extension ORDER BY extname;"
```

Verify:

- service is active after boot
- data lives on persistent local storage
- PostgreSQL parameters applied after restart
- required extensions are available

## Upgrades

```bash
psql -h localhost -U postgres -c "SELECT version();"
sudo yum update -y alloydbomni
sudo systemctl restart alloydb-omni
psql -h localhost -U postgres -c "SELECT version();"
```

After upgrades:

- confirm the service restarted cleanly
- re-check extension availability
- review `journalctl -u alloydb-omni` for startup warnings
- run representative health and query checks before handing the system back to users
