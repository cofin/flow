-- name: init-schema
-- dialect: duckdb
-- slot: vec_type = FLOAT[256]
CREATE TABLE IF NOT EXISTS catalog_meta (
    meta_key VARCHAR PRIMARY KEY,
    meta_value VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id VARCHAR PRIMARY KEY,
    repo_name VARCHAR NOT NULL,
    root_path VARCHAR NOT NULL,
    bundle_root VARCHAR NOT NULL,
    okf_version VARCHAR NOT NULL,
    indexed_at VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS entries (
    entry_id VARCHAR PRIMARY KEY,
    workspace_id VARCHAR NOT NULL,
    rel_path VARCHAR NOT NULL,
    concept_id VARCHAR NOT NULL,
    concept_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    description VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    state VARCHAR,
    trust_tier VARCHAR NOT NULL,
    verified_by VARCHAR,
    verified_at VARCHAR,
    tags VARCHAR[] NOT NULL,
    truth_block VARCHAR,
    body_markdown VARCHAR NOT NULL,
    frontmatter_json VARCHAR NOT NULL,
    content_sha256 VARCHAR NOT NULL,
    mtime_ms BIGINT NOT NULL,
    file_size BIGINT NOT NULL,
    doc_len INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS entry_terms (
    entry_id VARCHAR NOT NULL,
    term VARCHAR NOT NULL,
    tf INTEGER NOT NULL,
    PRIMARY KEY (entry_id, term)
);

CREATE INDEX IF NOT EXISTS idx_entry_terms_term ON entry_terms (term);

CREATE TABLE IF NOT EXISTS corpus_stats (
    stats_key INTEGER PRIMARY KEY,
    doc_count INTEGER NOT NULL,
    avg_doc_len DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS entry_sources (
    entry_id VARCHAR NOT NULL,
    source_id VARCHAR NOT NULL,
    resource VARCHAR NOT NULL,
    file_path VARCHAR,
    symbol_name VARCHAR,
    title VARCHAR,
    resource_exists BOOLEAN NOT NULL,
    PRIMARY KEY (entry_id, source_id)
);

CREATE INDEX IF NOT EXISTS idx_entry_sources_path ON entry_sources (file_path);

CREATE TABLE IF NOT EXISTS entry_links (
    from_entry_id VARCHAR NOT NULL,
    to_target VARCHAR NOT NULL,
    to_entry_id VARCHAR,
    edge_kind VARCHAR NOT NULL,
    target_exists BOOLEAN NOT NULL,
    PRIMARY KEY (from_entry_id, to_target, edge_kind)
);

CREATE INDEX IF NOT EXISTS idx_entry_links_to_entry ON entry_links (to_entry_id);

CREATE TABLE IF NOT EXISTS embedding_cache (
    content_sha256 VARCHAR NOT NULL,
    model_name VARCHAR NOT NULL,
    embedding_dim INTEGER NOT NULL,
    embedding /* slot: vec_type */ NOT NULL,
    PRIMARY KEY (content_sha256, model_name, embedding_dim)
);

CREATE TABLE IF NOT EXISTS entry_embeddings (
    entry_id VARCHAR NOT NULL,
    model_name VARCHAR NOT NULL,
    embedding_dim INTEGER NOT NULL,
    embedding /* slot: vec_type */ NOT NULL,
    PRIMARY KEY (entry_id, model_name)
);

-- name: refresh-corpus-stats
-- dialect: duckdb
INSERT OR REPLACE INTO corpus_stats (stats_key, doc_count, avg_doc_len)
SELECT
    1 AS stats_key,
    COUNT(*)::INTEGER AS doc_count,
    COALESCE(AVG(NULLIF(doc_len, 0)), 1.0) AS avg_doc_len
FROM entries;

-- name: select-workspace-manifest
-- dialect: duckdb
SELECT
    entry_id,
    rel_path,
    content_sha256,
    mtime_ms,
    file_size
FROM entries
WHERE workspace_id = :workspace_id;

-- name: select-missing-workspace-embeddings
-- dialect: duckdb
WITH current_model_embeddings AS (
    SELECT
        entry_id
    FROM entry_embeddings
    WHERE model_name = :model_name
),
current_model_cache AS (
    SELECT
        content_sha256,
        embedding
    FROM embedding_cache
    WHERE model_name = :model_name
      AND embedding_dim = :dim
)
SELECT
    e.entry_id,
    e.title,
    e.description,
    e.truth_block,
    e.body_markdown,
    e.content_sha256,
    cmc.embedding AS cached_vec
FROM entries AS e
LEFT JOIN current_model_embeddings AS cme
    ON cme.entry_id = e.entry_id
LEFT JOIN current_model_cache AS cmc
    ON cmc.content_sha256 = e.content_sha256
WHERE e.workspace_id = :workspace_id
  AND cme.entry_id IS NULL;

-- name: search-fts-bm25
-- dialect: duckdb
WITH scored AS (
    SELECT
        e.entry_id,
        fts_main_entries.match_bm25(
            e.entry_id,
            :query_text,
            fields := 'title,description,truth_block,body_markdown'
        ) AS bm25_score
    FROM entries AS e
    WHERE (:workspace_id IS NULL OR e.workspace_id = :workspace_id)
      AND (:concept_type IS NULL OR e.concept_type = :concept_type)
      AND (:trust_tier IS NULL OR e.trust_tier = :trust_tier)
)
SELECT
    e.entry_id,
    e.workspace_id,
    e.rel_path,
    e.concept_id,
    e.concept_type,
    e.title,
    e.description,
    e.trust_tier,
    e.truth_block,
    e.status,
    e.state,
    s.bm25_score,
    CAST(NULL AS DOUBLE) AS semantic_score,
    s.bm25_score AS rrf_score
FROM scored AS s
INNER JOIN entries AS e
    ON e.entry_id = s.entry_id
WHERE s.bm25_score IS NOT NULL
ORDER BY s.bm25_score DESC, e.entry_id ASC
LIMIT :limit_rows;

-- name: search-sql-bm25
-- dialect: duckdb
WITH query_tokens AS (
    SELECT DISTINCT
        1 AS stats_key,
        UNNEST(CAST(:query_terms AS VARCHAR[])) AS term
),
term_df AS (
    SELECT
        qt.term,
        qt.stats_key,
        COUNT(et.entry_id)::DOUBLE AS df
    FROM query_tokens AS qt
    LEFT JOIN entry_terms AS et
        ON et.term = qt.term
    GROUP BY qt.term, qt.stats_key
),
term_idf AS (
    SELECT
        td.term,
        LN(1.0 + ((GREATEST(cs.doc_count::DOUBLE - td.df + 0.5, 0.5)) / (td.df + 0.5))) AS idf,
        GREATEST(cs.avg_doc_len, 1.0) AS avg_doc_len
    FROM term_df AS td
    INNER JOIN corpus_stats AS cs
        ON cs.stats_key = td.stats_key
    WHERE td.df > 0
),
scored AS (
    SELECT
        et.entry_id,
        SUM(
            ti.idf * ((et.tf::DOUBLE * 2.2) / (et.tf::DOUBLE + 1.2 * (0.25 + 0.75 * (e.doc_len::DOUBLE / ti.avg_doc_len))))
        ) AS bm25_score
    FROM entry_terms AS et
    INNER JOIN term_idf AS ti
        ON ti.term = et.term
    INNER JOIN entries AS e
        ON e.entry_id = et.entry_id
    WHERE (:workspace_id IS NULL OR e.workspace_id = :workspace_id)
      AND (:concept_type IS NULL OR e.concept_type = :concept_type)
      AND (:trust_tier IS NULL OR e.trust_tier = :trust_tier)
    GROUP BY et.entry_id
)
SELECT
    e.entry_id,
    e.workspace_id,
    e.rel_path,
    e.concept_id,
    e.concept_type,
    e.title,
    e.description,
    e.trust_tier,
    e.truth_block,
    e.status,
    e.state,
    s.bm25_score,
    CAST(NULL AS DOUBLE) AS semantic_score,
    s.bm25_score AS rrf_score
FROM scored AS s
INNER JOIN entries AS e
    ON e.entry_id = s.entry_id
ORDER BY s.bm25_score DESC, e.entry_id ASC
LIMIT :limit_rows;

-- name: search-semantic
-- dialect: duckdb
-- slot: vec_type = FLOAT[256]
WITH vector_hits AS (
    SELECT
        ev.entry_id,
        1.0 - array_cosine_distance(ev.embedding, CAST(:query_vec AS /* slot: vec_type */)) AS semantic_score
    FROM entry_embeddings AS ev
    WHERE ev.model_name = :model_name
)
SELECT
    e.entry_id,
    e.workspace_id,
    e.rel_path,
    e.concept_id,
    e.concept_type,
    e.title,
    e.description,
    e.trust_tier,
    e.truth_block,
    e.status,
    e.state,
    CAST(NULL AS DOUBLE) AS bm25_score,
    v.semantic_score,
    v.semantic_score AS rrf_score
FROM vector_hits AS v
INNER JOIN entries AS e
    ON e.entry_id = v.entry_id
WHERE (:workspace_id IS NULL OR e.workspace_id = :workspace_id)
  AND (:concept_type IS NULL OR e.concept_type = :concept_type)
  AND (:trust_tier IS NULL OR e.trust_tier = :trust_tier)
ORDER BY v.semantic_score DESC, e.entry_id ASC
LIMIT :limit_rows;

-- name: search-hybrid-fts-rrf
-- dialect: duckdb
-- slot: vec_type = FLOAT[256]
WITH filtered_entries AS (
    SELECT
        e.entry_id
    FROM entries AS e
    WHERE (:workspace_id IS NULL OR e.workspace_id = :workspace_id)
      AND (:concept_type IS NULL OR e.concept_type = :concept_type)
      AND (:trust_tier IS NULL OR e.trust_tier = :trust_tier)
),
bm25_raw AS (
    SELECT
        fe.entry_id,
        fts_main_entries.match_bm25(
            fe.entry_id,
            :query_text,
            fields := 'title,description,truth_block,body_markdown'
        ) AS bm25_score
    FROM filtered_entries AS fe
),
bm25_hits AS (
    SELECT
        br.entry_id,
        br.bm25_score,
        ROW_NUMBER() OVER (ORDER BY br.bm25_score DESC, br.entry_id ASC) AS bm25_rank
    FROM bm25_raw AS br
    WHERE br.bm25_score IS NOT NULL
    LIMIT 100
),
vector_raw AS (
    SELECT
        ev.entry_id,
        1.0 - array_cosine_distance(ev.embedding, CAST(:query_vec AS /* slot: vec_type */)) AS semantic_score
    FROM entry_embeddings AS ev
    INNER JOIN filtered_entries AS fe
        ON fe.entry_id = ev.entry_id
    WHERE ev.model_name = :model_name
),
vector_hits AS (
    SELECT
        vr.entry_id,
        vr.semantic_score,
        ROW_NUMBER() OVER (ORDER BY vr.semantic_score DESC, vr.entry_id ASC) AS vec_rank
    FROM vector_raw AS vr
    LIMIT 100
),
fused AS (
    SELECT
        COALESCE(b.entry_id, v.entry_id) AS entry_id,
        b.bm25_score,
        v.semantic_score,
        COALESCE(1.0 / (60.0 + b.bm25_rank), 0.0)
            + COALESCE(1.0 / (60.0 + v.vec_rank), 0.0) AS rrf_score
    FROM bm25_hits AS b
    FULL OUTER JOIN vector_hits AS v
        ON b.entry_id = v.entry_id
)
SELECT
    e.entry_id,
    e.workspace_id,
    e.rel_path,
    e.concept_id,
    e.concept_type,
    e.title,
    e.description,
    e.trust_tier,
    e.truth_block,
    e.status,
    e.state,
    f.bm25_score,
    f.semantic_score,
    f.rrf_score
FROM fused AS f
INNER JOIN entries AS e
    ON e.entry_id = f.entry_id
ORDER BY f.rrf_score DESC, e.entry_id ASC
LIMIT :limit_rows;

-- name: search-hybrid-sql-rrf
-- dialect: duckdb
-- slot: vec_type = FLOAT[256]
WITH filtered_entries AS (
    SELECT
        e.entry_id,
        e.doc_len
    FROM entries AS e
    WHERE (:workspace_id IS NULL OR e.workspace_id = :workspace_id)
      AND (:concept_type IS NULL OR e.concept_type = :concept_type)
      AND (:trust_tier IS NULL OR e.trust_tier = :trust_tier)
),
query_tokens AS (
    SELECT DISTINCT
        1 AS stats_key,
        UNNEST(CAST(:query_terms AS VARCHAR[])) AS term
),
term_df AS (
    SELECT
        qt.term,
        qt.stats_key,
        COUNT(et.entry_id)::DOUBLE AS df
    FROM query_tokens AS qt
    LEFT JOIN entry_terms AS et
        ON et.term = qt.term
    GROUP BY qt.term, qt.stats_key
),
term_idf AS (
    SELECT
        td.term,
        LN(1.0 + ((GREATEST(cs.doc_count::DOUBLE - td.df + 0.5, 0.5)) / (td.df + 0.5))) AS idf,
        GREATEST(cs.avg_doc_len, 1.0) AS avg_doc_len
    FROM term_df AS td
    INNER JOIN corpus_stats AS cs
        ON cs.stats_key = td.stats_key
    WHERE td.df > 0
),
bm25_raw AS (
    SELECT
        et.entry_id,
        SUM(
            ti.idf * ((et.tf::DOUBLE * 2.2) / (et.tf::DOUBLE + 1.2 * (0.25 + 0.75 * (fe.doc_len::DOUBLE / ti.avg_doc_len))))
        ) AS bm25_score
    FROM entry_terms AS et
    INNER JOIN term_idf AS ti
        ON ti.term = et.term
    INNER JOIN filtered_entries AS fe
        ON fe.entry_id = et.entry_id
    GROUP BY et.entry_id
),
bm25_hits AS (
    SELECT
        br.entry_id,
        br.bm25_score,
        ROW_NUMBER() OVER (ORDER BY br.bm25_score DESC, br.entry_id ASC) AS bm25_rank
    FROM bm25_raw AS br
    LIMIT 100
),
vector_raw AS (
    SELECT
        ev.entry_id,
        1.0 - array_cosine_distance(ev.embedding, CAST(:query_vec AS /* slot: vec_type */)) AS semantic_score
    FROM entry_embeddings AS ev
    INNER JOIN filtered_entries AS fe
        ON fe.entry_id = ev.entry_id
    WHERE ev.model_name = :model_name
),
vector_hits AS (
    SELECT
        vr.entry_id,
        vr.semantic_score,
        ROW_NUMBER() OVER (ORDER BY vr.semantic_score DESC, vr.entry_id ASC) AS vec_rank
    FROM vector_raw AS vr
    LIMIT 100
),
fused AS (
    SELECT
        COALESCE(b.entry_id, v.entry_id) AS entry_id,
        b.bm25_score,
        v.semantic_score,
        COALESCE(1.0 / (60.0 + b.bm25_rank), 0.0)
            + COALESCE(1.0 / (60.0 + v.vec_rank), 0.0) AS rrf_score
    FROM bm25_hits AS b
    FULL OUTER JOIN vector_hits AS v
        ON b.entry_id = v.entry_id
)
SELECT
    e.entry_id,
    e.workspace_id,
    e.rel_path,
    e.concept_id,
    e.concept_type,
    e.title,
    e.description,
    e.trust_tier,
    e.truth_block,
    e.status,
    e.state,
    f.bm25_score,
    f.semantic_score,
    f.rrf_score
FROM fused AS f
INNER JOIN entries AS e
    ON e.entry_id = f.entry_id
ORDER BY f.rrf_score DESC, e.entry_id ASC
LIMIT :limit_rows;

-- name: find-provenance
-- dialect: duckdb
WITH matched_entries AS (
    SELECT
        s.entry_id,
        COUNT(*)::DOUBLE AS citation_count
    FROM entry_sources AS s
    WHERE s.file_path = :file_path
       OR s.file_path LIKE :suffix_pattern
       OR s.resource = :file_path
       OR s.resource LIKE :prefix_pattern
    GROUP BY s.entry_id
)
SELECT
    e.entry_id,
    e.workspace_id,
    e.rel_path,
    e.concept_id,
    e.concept_type,
    e.title,
    e.description,
    e.trust_tier,
    e.truth_block,
    e.status,
    e.state,
    CAST(NULL AS DOUBLE) AS bm25_score,
    CAST(NULL AS DOUBLE) AS semantic_score,
    me.citation_count AS rrf_score
FROM matched_entries AS me
INNER JOIN entries AS e
    ON e.entry_id = me.entry_id
WHERE (:workspace_id IS NULL OR e.workspace_id = :workspace_id)
ORDER BY me.citation_count DESC, e.title ASC
LIMIT :limit_rows;

-- name: select-entry-by-id
-- dialect: duckdb
SELECT
    entry_id,
    workspace_id,
    rel_path,
    concept_id,
    concept_type,
    title,
    description,
    status,
    state,
    trust_tier,
    verified_by,
    verified_at,
    tags,
    truth_block,
    body_markdown,
    frontmatter_json,
    content_sha256,
    mtime_ms,
    file_size
FROM entries
WHERE entry_id = :entry_id;

-- name: select-entry-sources
-- dialect: duckdb
SELECT
    entry_id,
    source_id,
    resource,
    file_path,
    symbol_name,
    title,
    resource_exists
FROM entry_sources
WHERE entry_id = :entry_id
ORDER BY source_id ASC;

-- name: select-outbound-links
-- dialect: duckdb
SELECT
    from_entry_id,
    to_target,
    to_entry_id,
    edge_kind,
    target_exists
FROM entry_links
WHERE from_entry_id = :entry_id
ORDER BY to_target ASC;

-- name: select-inbound-links
-- dialect: duckdb
SELECT
    from_entry_id,
    to_target,
    to_entry_id,
    edge_kind,
    target_exists
FROM entry_links
WHERE to_entry_id = :entry_id
ORDER BY from_entry_id ASC;

-- name: select-workspace-facets
-- dialect: duckdb
SELECT
    workspace_id AS value,
    COUNT(*)::INTEGER AS count
FROM entries
GROUP BY workspace_id
ORDER BY count DESC, value ASC;

-- name: select-type-facets
-- dialect: duckdb
SELECT
    concept_type AS value,
    COUNT(*)::INTEGER AS count
FROM entries
GROUP BY concept_type
ORDER BY count DESC, value ASC;

-- name: select-trust-facets
-- dialect: duckdb
SELECT
    trust_tier AS value,
    COUNT(*)::INTEGER AS count
FROM entries
GROUP BY trust_tier
ORDER BY count DESC, value ASC;

-- name: select-broken-links
-- dialect: duckdb
SELECT
    e.entry_id,
    e.workspace_id,
    e.rel_path,
    e.title,
    'broken_link' AS issue_kind,
    l.to_target AS target
FROM entry_links AS l
INNER JOIN entries AS e
    ON e.entry_id = l.from_entry_id
WHERE l.target_exists = FALSE
  AND (:workspace_id IS NULL OR e.workspace_id = :workspace_id)
ORDER BY e.workspace_id ASC, e.rel_path ASC, l.to_target ASC;

-- name: select-missing-sources
-- dialect: duckdb
SELECT
    e.entry_id,
    e.workspace_id,
    e.rel_path,
    e.title,
    'missing_source' AS issue_kind,
    s.resource AS target
FROM entry_sources AS s
INNER JOIN entries AS e
    ON e.entry_id = s.entry_id
WHERE s.resource_exists = FALSE
  AND (:workspace_id IS NULL OR e.workspace_id = :workspace_id)
ORDER BY e.workspace_id ASC, e.rel_path ASC, s.resource ASC;
