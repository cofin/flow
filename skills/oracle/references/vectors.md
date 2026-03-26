# Oracle AI Vector Search

## Overview

Oracle Database 23ai introduced native vector support for AI-powered similarity search. The VECTOR data type, distance functions, and approximate nearest neighbor (ANN) indexes enable embedding storage and retrieval directly inside the database — no external vector database required.

## VECTOR Data Type

```sql
-- Fixed-dimension vector (recommended when dimension is known)
CREATE TABLE documents (
    id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title       VARCHAR2(200),
    content     CLOB,
    embedding   VECTOR(1536, FLOAT32)   -- 1536 dimensions, 32-bit floats
);

-- Flexible-dimension vector
CREATE TABLE multi_model_embeddings (
    id          NUMBER PRIMARY KEY,
    model_name  VARCHAR2(100),
    embedding   VECTOR(*, FLOAT32)      -- any dimension
);

-- Supported element types
-- FLOAT32  (default, best compatibility)
-- FLOAT64  (double precision, rarely needed)
-- INT8     (quantized, 4x smaller, slight quality loss)
-- BINARY   (bit-packed, 32x smaller, for binary embeddings)
```

### Inserting Vectors

```sql
-- From a literal array
INSERT INTO documents (title, embedding)
VALUES ('Oracle AI', VECTOR('[0.1, 0.2, 0.3, ...]', 1536, FLOAT32));

-- From Python with python-oracledb
import oracledb
import numpy as np

embedding = np.random.rand(1536).astype(np.float32)
cursor.execute(
    "INSERT INTO documents (title, embedding) VALUES (:1, :2)",
    ["My Document", embedding.tobytes()]
)
```

## Distance Functions

Oracle supports multiple distance metrics for similarity comparison:

```sql
-- Cosine distance (most common for text embeddings, normalized vectors)
SELECT title, VECTOR_DISTANCE(embedding, :query_vec, COSINE) AS distance
FROM documents
ORDER BY distance
FETCH FIRST 10 ROWS ONLY;

-- Euclidean (L2) distance
SELECT title, VECTOR_DISTANCE(embedding, :query_vec, EUCLIDEAN) AS distance
FROM documents
ORDER BY distance
FETCH FIRST 10 ROWS ONLY;

-- Dot product (for unnormalized vectors, higher = more similar)
SELECT title, VECTOR_DISTANCE(embedding, :query_vec, DOT) AS similarity
FROM documents
ORDER BY similarity DESC
FETCH FIRST 10 ROWS ONLY;

-- Manhattan (L1) distance
SELECT title, VECTOR_DISTANCE(embedding, :query_vec, MANHATTAN) AS distance
FROM documents
ORDER BY distance
FETCH FIRST 10 ROWS ONLY;

-- Hamming distance (for BINARY vectors)
SELECT title, VECTOR_DISTANCE(embedding, :query_vec, HAMMING) AS distance
FROM documents
ORDER BY distance
FETCH FIRST 10 ROWS ONLY;
```

### Shorthand Operators

```sql
-- Cosine distance shorthand (< = > operator)
SELECT title FROM documents
ORDER BY embedding <=> :query_vec
FETCH FIRST 10 ROWS ONLY;
```

## Vector Indexes (ANN)

Approximate Nearest Neighbor indexes trade slight accuracy for dramatically faster search at scale.

### IVF (Inverted File) Index

Partitions vectors into clusters. Best for datasets where you can tolerate some accuracy loss for speed.

```sql
-- Create IVF index
CREATE VECTOR INDEX doc_embed_ivf_idx ON documents (embedding)
ORGANIZATION NEIGHBOR PARTITIONS
WITH DISTANCE COSINE
PARAMETERS (TYPE IVF, NEIGHBOR PARTITIONS 64);

-- Query with ANN (uses index automatically when available)
SELECT title, VECTOR_DISTANCE(embedding, :query_vec, COSINE) AS dist
FROM documents
ORDER BY dist
FETCH APPROXIMATE FIRST 10 ROWS ONLY;
```

### HNSW (Hierarchical Navigable Small World) Index

Graph-based index with better recall than IVF at similar speed. Preferred for most use cases.

```sql
CREATE VECTOR INDEX doc_embed_hnsw_idx ON documents (embedding)
ORGANIZATION INMEMORY NEIGHBOR GRAPH
WITH DISTANCE COSINE
PARAMETERS (TYPE HNSW, M 16, EFCONSTRUCTION 200);

-- HNSW parameters:
-- M              : max connections per node (higher = better recall, more memory). Default 16.
-- EFCONSTRUCTION : search width during build (higher = better index quality, slower build). Default 200.
```

### Choosing Between IVF and HNSW

| Factor | IVF | HNSW |
|--------|-----|------|
| Build speed | Faster | Slower |
| Query speed | Fast | Faster |
| Recall accuracy | Good (~90-95%) | Better (~95-99%) |
| Memory usage | Lower | Higher |
| Update cost | Requires rebuild | Incremental |
| Best for | Large static datasets | Dynamic datasets, high recall needs |

## Embedding Generation (In-Database)

Oracle 23ai can generate embeddings directly using DBMS_VECTOR:

```sql
-- Generate embedding using a configured model
SELECT DBMS_VECTOR.UTL_TO_EMBEDDING(
    'What is Oracle AI Vector Search?',
    JSON('{"provider": "ocigenai", "model": "cohere.embed-english-v3.0"}')
) AS embedding
FROM DUAL;

-- Batch embedding generation
INSERT INTO documents (title, content, embedding)
SELECT title, content,
       DBMS_VECTOR.UTL_TO_EMBEDDING(content,
           JSON('{"provider": "ocigenai", "model": "cohere.embed-english-v3.0"}'))
FROM source_documents;
```

### Supported Providers

- **OCI GenAI**: Cohere, Meta Llama embeddings
- **OpenAI**: text-embedding-ada-002, text-embedding-3-small/large
- **Cohere**: embed-english-v3.0, embed-multilingual-v3.0
- **Custom**: ONNX models loaded into the database

### Configuring Credentials

```sql
-- Create credential for OCI GenAI
BEGIN
    DBMS_CLOUD.CREATE_CREDENTIAL(
        credential_name => 'OCI_GENAI_CRED',
        user_ocid       => 'ocid1.user.oc1...',
        tenancy_ocid    => 'ocid1.tenancy.oc1...',
        private_key     => '<private-key>',
        fingerprint     => '...'
    );
END;
/

-- Create credential for OpenAI
BEGIN
    DBMS_CLOUD.CREATE_CREDENTIAL(
        credential_name => 'OPENAI_CRED',
        username        => 'OPENAI',
        password        => '<api-key>'
    );
END;
/
```

## RAG (Retrieval-Augmented Generation) Pattern

Combine vector search with LLM generation entirely in SQL:

```sql
-- Step 1: Find relevant context via vector search
WITH context AS (
    SELECT content,
           VECTOR_DISTANCE(embedding, :query_embedding, COSINE) AS distance
    FROM knowledge_base
    ORDER BY distance
    FETCH APPROXIMATE FIRST 5 ROWS ONLY
)
-- Step 2: Generate answer using retrieved context
SELECT DBMS_VECTOR_CHAIN.UTL_TO_GENERATE_TEXT(
    'Answer the question based on the context below.' || CHR(10) ||
    'Context: ' || LISTAGG(content, CHR(10)) WITHIN GROUP (ORDER BY distance) || CHR(10) ||
    'Question: ' || :user_question,
    JSON('{"provider": "ocigenai", "model": "cohere.command-r-plus"}')
) AS answer
FROM context;
```

## Hybrid Search

Combine vector similarity with traditional SQL filtering for more precise results:

```sql
-- Vector search with metadata filters
SELECT d.title, d.category,
       VECTOR_DISTANCE(d.embedding, :query_vec, COSINE) AS distance
FROM documents d
WHERE d.category = 'technical'
  AND d.created_at > SYSDATE - 90
  AND d.is_published = 1
ORDER BY distance
FETCH APPROXIMATE FIRST 10 ROWS ONLY;

-- Combined full-text + vector search
SELECT d.title,
       VECTOR_DISTANCE(d.embedding, :query_vec, COSINE) AS vec_dist,
       SCORE(1) AS text_score
FROM documents d
WHERE CONTAINS(d.content, :text_query, 1) > 0
ORDER BY (0.7 * (1 - vec_dist) + 0.3 * SCORE(1)) DESC
FETCH FIRST 10 ROWS ONLY;
```

## Vector Utilities

```sql
-- Get vector dimension
SELECT VECTOR_DIMENSION_COUNT(embedding) FROM documents WHERE ROWNUM = 1;

-- Get vector norm (magnitude)
SELECT VECTOR_NORM(embedding) FROM documents WHERE ROWNUM = 1;

-- Convert between formats
SELECT TO_VECTOR('[1.0, 2.0, 3.0]', 3, FLOAT32) FROM DUAL;

-- Serialize vector to string
SELECT FROM_VECTOR(embedding) FROM documents WHERE ROWNUM = 1;
```

## Best Practices

- **Normalize vectors** before storage if using cosine distance — pre-normalized vectors make cosine equivalent to dot product, which is faster
- **Choose dimension wisely**: 1536 (OpenAI ada-002) or 1024 (Cohere v3) are common. Smaller dimensions (384-768) trade accuracy for speed and storage
- **Use INT8 quantization** for large-scale deployments where slight recall loss is acceptable — reduces storage by 4x
- **Create HNSW indexes** for most use cases; use IVF only when memory is constrained
- **Batch insert** embeddings rather than one-at-a-time for throughput
- **Monitor recall**: compare ANN results (FETCH APPROXIMATE) against exact search periodically to validate index quality
- **Partition large tables** by category or date, with per-partition vector indexes for faster pruning

## Official References

- Oracle AI Vector Search Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/>
- DBMS_VECTOR Package: <https://docs.oracle.com/en/database/oracle/oracle-database/23/arpls/dbms_vector.html>
- VECTOR Data Type: <https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Data-Types.html>
- Oracle AI Vector Search Blog: <https://blogs.oracle.com/database/post/oracle-announces-general-availability-of-ai-vector-search-in-oracle-database-23ai>
