# JSON/JSONB Patterns

## JSONB vs JSON

| Feature | `jsonb` | `json` |
|---------|---------|--------|
| Storage | Decomposed binary | Raw text |
| Duplicate keys | Last value wins | All kept |
| Key ordering | Not preserved | Preserved |
| Indexing (GIN) | Yes | No |
| Operators (@>, ?, etc.) | Yes | No |
| Speed (read) | Faster | Slower (re-parsed each time) |
| Speed (write) | Slightly slower (conversion) | Faster |

**Use JSONB almost always.** Use JSON only when you need exact text preservation or duplicate keys.

## Operators

```sql
-- Navigation operators
SELECT data->'address'          -- jsonb: returns JSONB object
FROM documents;

SELECT data->>'name'            -- text: returns text value
FROM documents;

SELECT data#>'{address,city}'   -- jsonb: path navigation, returns JSONB
FROM documents;

SELECT data#>>'{tags,0}'       -- text: path navigation, returns text
FROM documents;

-- Containment
SELECT * FROM docs WHERE data @> '{"status": "active"}';     -- left contains right
SELECT * FROM docs WHERE '{"status": "active"}' <@ data;     -- right contains left

-- Existence
SELECT * FROM docs WHERE data ? 'email';                     -- key exists
SELECT * FROM docs WHERE data ?| ARRAY['email', 'phone'];   -- any key exists
SELECT * FROM docs WHERE data ?& ARRAY['email', 'phone'];   -- all keys exist

-- Equality
SELECT * FROM docs WHERE data->'address' = '{"city": "NYC"}'::jsonb;
```

## Building JSON/JSONB

```sql
-- Build objects
SELECT jsonb_build_object(
    'id', u.id,
    'name', u.name,
    'email', u.email,
    'address', jsonb_build_object('city', a.city, 'state', a.state)
)
FROM users u JOIN addresses a ON a.user_id = u.id;

-- Build arrays
SELECT jsonb_build_array(1, 'two', true, null);
-- [1, "two", true, null]

-- Aggregate rows into a JSON array
SELECT jsonb_agg(
    jsonb_build_object('id', id, 'name', name)
    ORDER BY name
)
FROM users WHERE active;
-- [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

-- Aggregate key-value pairs into an object
SELECT jsonb_object_agg(key, value)
FROM settings;
-- {"theme": "dark", "lang": "en"}

-- From row to JSON
SELECT to_jsonb(u.*) FROM users u WHERE id = 1;
-- {"id": 1, "name": "Alice", "email": "alice@example.com", ...}
```

## SQL/JSON Path Language (PG12+)

```sql
-- jsonb_path_query: extract matching values
SELECT jsonb_path_query(data, '$.tags[*] ? (@ starts with "pg")')
FROM documents;

-- jsonb_path_exists: check if path matches
SELECT * FROM documents
WHERE jsonb_path_exists(data, '$.tags[*] ? (@ == "postgres")');

-- jsonb_path_query_array: return matches as array
SELECT jsonb_path_query_array(data, '$.items[*].price ? (@ > 100)')
FROM orders;

-- jsonb_path_query_first: first match only
SELECT jsonb_path_query_first(data, '$.items[0].name')
FROM orders;

-- Path expressions with filters
-- $          root
-- .key       object member
-- [*]        all array elements
-- [0]        array index
-- ?()        filter expression
-- @          current item in filter

-- Examples:
-- '$.address.city'                    -> navigate to city
-- '$.items[*].price ? (@ > 50)'      -> prices over 50
-- '$.users[*] ? (@.age >= 18)'       -> users 18+
-- '$.items[*] ? (@.qty > 0).name'    -> names where qty > 0
```

## GIN Indexing for JSONB

```sql
-- Default GIN index: supports @>, ?, ?|, ?&
CREATE INDEX idx_docs_data ON documents USING gin (data);

-- jsonb_path_ops: supports only @>, but smaller and faster
CREATE INDEX idx_docs_data_pathops ON documents USING gin (data jsonb_path_ops);

-- Index a specific key (for targeted queries)
CREATE INDEX idx_docs_status ON documents USING btree ((data->>'status'));
CREATE INDEX idx_docs_score ON documents USING btree (((data->>'score')::int));

-- GIN on a nested path
CREATE INDEX idx_docs_tags ON documents USING gin ((data->'tags'));
-- Supports: WHERE data->'tags' @> '["postgres"]'

-- jsonb_path_ops is preferred when you only use @> containment queries
-- Default ops is needed for ?, ?|, ?& existence checks
```

## Modifying JSONB

```sql
-- Concatenation (merge / overwrite)
UPDATE docs SET data = data || '{"status": "archived", "priority": 1}'::jsonb
WHERE id = 1;

-- Remove a key
UPDATE docs SET data = data - 'temp_field' WHERE id = 1;

-- Remove nested key by path
UPDATE docs SET data = data #- '{address,zip}' WHERE id = 1;

-- Remove array element by index
UPDATE docs SET data = data - 0 WHERE id = 1;  -- remove first element (if array)

-- jsonb_set: set a value at a path
UPDATE docs SET data = jsonb_set(data, '{address,city}', '"Boston"')
WHERE id = 1;

-- jsonb_set with create_if_missing (default true)
UPDATE docs SET data = jsonb_set(data, '{new_field}', '"new_value"', true)
WHERE id = 1;

-- jsonb_insert: insert into arrays
UPDATE docs SET data = jsonb_insert(data, '{tags,0}', '"urgent"')
WHERE id = 1;
-- Inserts "urgent" at position 0 of tags array

-- Deep merge (recursive, custom function often needed)
-- Simple top-level merge uses ||
UPDATE docs SET data = data || '{"score": 5}'::jsonb;
```

## Querying Nested Structures Efficiently

```sql
-- Expand JSONB array into rows
SELECT d.id, tag.value AS tag
FROM documents d,
     jsonb_array_elements_text(d.data->'tags') AS tag(value);

-- Expand JSONB object into key-value rows
SELECT d.id, kv.key, kv.value
FROM documents d,
     jsonb_each_text(d.data->'metadata') AS kv(key, value);

-- Nested array of objects
SELECT
    o.id,
    item->>'name' AS item_name,
    (item->>'price')::numeric AS price,
    (item->>'qty')::int AS qty
FROM orders o,
     jsonb_array_elements(o.data->'items') AS item;

-- Aggregate back after expansion
SELECT o.id,
       sum((item->>'price')::numeric * (item->>'qty')::int) AS total
FROM orders o,
     jsonb_array_elements(o.data->'items') AS item
GROUP BY o.id;

-- EXISTS subquery pattern (often faster than @>)
SELECT * FROM orders
WHERE EXISTS (
    SELECT 1
    FROM jsonb_array_elements(data->'items') AS item
    WHERE (item->>'price')::numeric > 100
);
```

## Generated Columns from JSONB (PG12+)

```sql
-- Extract frequently-queried fields into generated columns
ALTER TABLE documents
    ADD COLUMN status text GENERATED ALWAYS AS (data->>'status') STORED;

ALTER TABLE documents
    ADD COLUMN score int GENERATED ALWAYS AS ((data->>'score')::int) STORED;

-- Now you can index the generated column directly
CREATE INDEX idx_docs_status ON documents (status);
CREATE INDEX idx_docs_score ON documents (score);

-- Queries can use either the generated column or the JSONB path
SELECT * FROM documents WHERE status = 'active';
-- Uses the B-tree index on the generated column
```

## Common Patterns

```sql
-- COALESCE with JSONB (handle missing keys)
SELECT COALESCE(data->>'nickname', data->>'name', 'Anonymous') AS display_name
FROM users;

-- Check for null vs missing key
SELECT *
FROM documents
WHERE data->'field' IS NOT NULL         -- key exists (value might be JSON null)
  AND data->>'field' IS NOT NULL;       -- key exists AND value is not JSON null

-- Type checking
SELECT *
FROM documents
WHERE jsonb_typeof(data->'tags') = 'array';

-- Pretty print
SELECT jsonb_pretty(data) FROM documents WHERE id = 1;
```
