# AlloyDB Features

## Columnar Engine

The columnar engine automatically caches frequently accessed columns in a columnar format for analytical queries.

```sql
-- Enable columnar engine on a table
SELECT google_columnar_engine_add('orders');

-- Check columnar engine status
SELECT * FROM g_columnar_recommended_columns;

-- Verify a query uses columnar engine
EXPLAIN (ANALYZE) SELECT region, SUM(amount) FROM orders GROUP BY region;
-- Look for "Columnar Scan" in the plan
```

### Automatic Column Selection

```sql
-- AlloyDB automatically recommends columns based on workload
-- View recommendations:
SELECT table_name, column_name, estimated_benefit
FROM g_columnar_recommended_columns
ORDER BY estimated_benefit DESC;
```

## Adaptive Caching

AlloyDB uses an intelligent caching layer that learns access patterns. No manual configuration needed, but you can monitor it:

```sql
-- Cache hit ratio
SELECT
    blks_hit::float / (blks_hit + blks_read) AS cache_hit_ratio
FROM pg_stat_database
WHERE datname = current_database();
```

## ML Embeddings & Vector Search

AlloyDB integrates with Vertex AI for generating embeddings directly in SQL.

```sql
-- Enable the extension
CREATE EXTENSION IF NOT EXISTS google_ml_integration;

-- Grant access
GRANT EXECUTE ON FUNCTION embedding TO app_user;

-- Generate embeddings using Vertex AI
SELECT embedding(
    'textembedding-gecko@003',
    'This is my document text'
) AS vector;

-- Store embeddings in a table
ALTER TABLE documents ADD COLUMN embedding vector(768);

UPDATE documents SET embedding = embedding(
    'textembedding-gecko@003',
    title || ' ' || content
);
```

## pgvector Integration

```sql
-- Install pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table with vector column
CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    description TEXT,
    embedding vector(768)
);

-- Create HNSW index (recommended for AlloyDB)
CREATE INDEX idx_items_embedding ON items
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

-- Similarity search
SELECT id, description,
       1 - (embedding <=> query_embedding) AS similarity
FROM items
ORDER BY embedding <=> query_embedding
LIMIT 10;

-- Hybrid search: combine vector similarity with filters
SELECT id, description
FROM items
WHERE category = 'electronics'
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

## AlloyDB AI Predictions

```sql
-- Register a Vertex AI model endpoint
CALL google_ml.create_model(
    model_id => 'my_model',
    model_provider => 'google',
    model_qualified_name => 'projects/my-project/locations/us-central1/endpoints/12345'
);

-- Use the model in SQL
SELECT id, google_ml.predict_row('my_model', json_build_object('features', features))
FROM predict_table;
```

## Automated Backups & PITR

```bash
# Backups are automatic (14-day retention by default)
# Configure continuous backup
gcloud alloydb clusters update my-cluster \
    --region=us-central1 \
    --continuous-backup-recovery-window-days=14 \
    --enable-continuous-backup

# Point-in-time restore
gcloud alloydb clusters restore my-cluster-restored \
    --region=us-central1 \
    --network=default \
    --source-cluster=my-cluster \
    --point-in-time="2024-06-15T14:30:00Z"
```
