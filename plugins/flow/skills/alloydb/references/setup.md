# AlloyDB Cluster Setup

## Prerequisites

```bash
# Enable the AlloyDB API
gcloud services enable alloydb.googleapis.com

# Enable Service Networking (for Private Service Access)
gcloud services enable servicenetworking.googleapis.com
```

## Private Service Access (Required)

AlloyDB instances are only accessible via private IP through VPC peering.

```bash
# Create an IP allocation for Google services
gcloud compute addresses create alloydb-range \
    --global \
    --purpose=VPC_PEERING \
    --prefix-length=16 \
    --network=default

# Create the private connection
gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges=alloydb-range \
    --network=default
```

## Create a Cluster

```bash
# Create cluster
gcloud alloydb clusters create my-cluster \
    --region=us-central1 \
    --network=default \
    --password=my-secure-password

# Create primary instance
gcloud alloydb instances create my-primary \
    --cluster=my-cluster \
    --region=us-central1 \
    --instance-type=PRIMARY \
    --cpu-count=4 \
    --database-flags=max_connections=500
```

## Read Pool Instances

```bash
# Create read pool (auto-scales read replicas)
gcloud alloydb instances create my-read-pool \
    --cluster=my-cluster \
    --region=us-central1 \
    --instance-type=READ_POOL \
    --cpu-count=4 \
    --read-pool-node-count=2
```

## Cross-Region Replication

```bash
# Create secondary cluster in another region
gcloud alloydb clusters create my-cluster-secondary \
    --region=europe-west1 \
    --network=default \
    --primary-cluster=projects/my-project/locations/us-central1/clusters/my-cluster

# Create secondary instance
gcloud alloydb instances create secondary-instance \
    --cluster=my-cluster-secondary \
    --region=europe-west1 \
    --instance-type=SECONDARY \
    --cpu-count=4
```

## Connecting

```bash
# From a GCE VM in the same VPC
psql "host=ALLOYDB_IP dbname=postgres user=postgres sslmode=require"

# Using AlloyDB Auth Proxy (recommended for external access)
./alloydb-auth-proxy \
    "projects/my-project/locations/us-central1/clusters/my-cluster/instances/my-primary" \
    --port=5432

# Then connect locally
psql "host=127.0.0.1 port=5432 dbname=postgres user=postgres"
```

## Terraform Example

```hcl
resource "google_alloydb_cluster" "default" {
  cluster_id = "my-cluster"
  location   = "us-central1"
  network_config {
    network = google_compute_network.default.id
  }
  initial_user {
    password = var.db_password
  }
}

resource "google_alloydb_instance" "primary" {
  cluster       = google_alloydb_cluster.default.name
  instance_id   = "my-primary"
  instance_type = "PRIMARY"
  machine_config {
    cpu_count = 4
  }
}
```
