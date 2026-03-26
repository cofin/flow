# DuckDB Key Function Reference

## Aggregate Functions

```sql
-- arg_min / arg_max: return the value of one column at the row where another is min/max
SELECT arg_min(name, salary) AS lowest_paid,
       arg_max(name, salary) AS highest_paid
FROM employees;

-- list_agg: collect values into a list
SELECT department, list(name ORDER BY name) AS members
FROM employees GROUP BY department;

-- string_agg: concatenate strings with separator
SELECT department, string_agg(name, ', ' ORDER BY name) AS names
FROM employees GROUP BY department;

-- approx_count_distinct: HyperLogLog approximate distinct count
SELECT approx_count_distinct(user_id) AS approx_users FROM events;

-- reservoir_sample: random sample of values
SELECT reservoir_quantile(value, 0.5) FROM measurements;

-- Quantile functions
SELECT quantile_cont(salary, 0.5) AS median,
       quantile_cont(salary, [0.25, 0.5, 0.75]) AS quartiles
FROM employees;

-- bitstring_agg: aggregate into bitstring
SELECT bitstring_agg(flag) FROM my_flags;

-- kurtosis, skewness, entropy
SELECT kurtosis(value), skewness(value), entropy(category)
FROM measurements;

-- first / last (with ordering)
SELECT first(price ORDER BY ts), last(price ORDER BY ts)
FROM trades WHERE symbol = 'AAPL';
```

---

## Date/Time Functions

```sql
-- date_trunc: truncate to specified precision
SELECT date_trunc('month', TIMESTAMP '2025-03-15 10:30:00');
-- 2025-03-01 00:00:00

-- date_part / extract: get component
SELECT date_part('year', DATE '2025-03-15');
SELECT extract(dow FROM DATE '2025-03-15');  -- day of week

-- date_diff: difference between dates
SELECT date_diff('day', DATE '2025-01-01', DATE '2025-03-15');
-- 73

-- date_add / date_sub
SELECT DATE '2025-01-01' + INTERVAL 30 DAY;
SELECT date_add(TIMESTAMP '2025-01-01', INTERVAL 3 MONTH);

-- generate_series: create date/time ranges
SELECT * FROM generate_series(DATE '2025-01-01', DATE '2025-12-31', INTERVAL 1 MONTH);

-- epoch conversions
SELECT epoch(TIMESTAMP '2025-01-01 00:00:00');          -- to epoch seconds
SELECT epoch_ms(1735689600000);                          -- from epoch milliseconds
SELECT make_timestamp(2025, 1, 15, 10, 30, 0);          -- from components

-- strftime / strptime: format / parse
SELECT strftime(CURRENT_TIMESTAMP, '%Y-%m-%d %H:%M');
SELECT strptime('2025-03-15', '%Y-%m-%d');

-- age: human-readable interval between dates
SELECT age(DATE '2025-03-15', DATE '2020-01-01');
-- 5 years 2 months 14 days

-- Current date/time
SELECT current_date, current_timestamp, now();

-- Timezone handling
SELECT TIMESTAMP '2025-01-01 12:00:00' AT TIME ZONE 'America/New_York';
```

---

## String Functions

```sql
-- regexp_extract: capture group from regex
SELECT regexp_extract('order-12345-US', 'order-(\d+)-(\w+)', 1);
-- '12345'

-- regexp_replace: substitute with regex
SELECT regexp_replace('2025-03-15', '(\d{4})-(\d{2})-(\d{2})', '\2/\3/\1');
-- '03/15/2025'

-- regexp_matches: check if pattern matches
SELECT regexp_matches('hello123', '\d+');  -- true

-- string_split: split into list
SELECT string_split('a,b,c', ',');
-- ['a', 'b', 'c']

-- string_split_regex
SELECT string_split_regex('one  two   three', '\s+');

-- format: printf-style formatting
SELECT format('{} has {} items', 'Cart', 42);
SELECT printf('%.2f%%', 99.1);

-- Padding and trimming
SELECT lpad('42', 5, '0');     -- '00042'
SELECT trim('  hello  ');       -- 'hello'
SELECT ltrim('xxhello', 'x');   -- 'hello'

-- contains, prefix, suffix
SELECT contains('hello world', 'world');        -- true
SELECT starts_with('hello', 'hel');             -- true
SELECT suffix('filename.parquet', '.parquet');   -- true

-- repeat, reverse, replace
SELECT repeat('ab', 3);     -- 'ababab'
SELECT reverse('hello');     -- 'olleh'
SELECT replace('foo bar', ' ', '_');  -- 'foo_bar'

-- length, position
SELECT length('hello');                  -- 5
SELECT position('world' IN 'hello world');  -- 7

-- ASCII / Unicode
SELECT ascii('A');      -- 65
SELECT chr(65);         -- 'A'
SELECT unicode('A');    -- 65
```

---

## List Functions

```sql
-- list_transform: apply lambda to each element
SELECT list_transform([1, 2, 3], x -> x * 10);
-- [10, 20, 30]

-- list_filter: keep elements matching predicate
SELECT list_filter(['apple', 'banana', 'avocado'], s -> s[1] = 'a');
-- ['apple', 'avocado']

-- list_reduce: fold to single value
SELECT list_reduce([1, 2, 3, 4], (acc, x) -> acc + x);
-- 10

-- list_sort / list_reverse_sort
SELECT list_sort([3, 1, 2]);           -- [1, 2, 3]
SELECT list_reverse_sort([3, 1, 2]);   -- [3, 2, 1]

-- flatten: collapse nested lists
SELECT flatten([[1, 2], [3, 4]]);
-- [1, 2, 3, 4]

-- unnest: expand list into rows
SELECT unnest([1, 2, 3]) AS val;
-- Returns 3 rows

-- list_aggregate: apply aggregate function to list
SELECT list_aggregate([1, 2, 3], 'sum');     -- 6
SELECT list_aggregate([1, 2, 3], 'avg');     -- 2.0

-- list_distinct / list_unique
SELECT list_distinct([1, 2, 2, 3]);  -- [1, 2, 3]

-- list_contains / list_has_any / list_has_all
SELECT list_contains([1, 2, 3], 2);                -- true
SELECT list_has_any([1, 2, 3], [2, 4]);            -- true
SELECT list_has_all([1, 2, 3], [1, 2]);            -- true

-- list_concat / list_append / list_prepend
SELECT list_concat([1, 2], [3, 4]);    -- [1, 2, 3, 4]
SELECT list_append([1, 2], 3);         -- [1, 2, 3]
SELECT list_prepend(0, [1, 2]);        -- [0, 1, 2]

-- array_length / list_count (alias len)
SELECT len([1, 2, 3]);  -- 3

-- generate_series as list
SELECT list(generate_series) FROM generate_series(1, 5);
```

---

## Struct Functions

```sql
-- struct_pack: create a struct
SELECT struct_pack(name := 'Alice', age := 30);

-- struct_extract: get field by name
SELECT struct_extract({'x': 1, 'y': 2}, 'x');
-- 1

-- Dot notation access
SELECT s.name FROM (SELECT {'name': 'Alice', 'age': 30} AS s);

-- row(): positional struct constructor
SELECT row(1, 'hello', 3.14);

-- struct_insert: add or overwrite fields
SELECT struct_insert({'a': 1, 'b': 2}, c := 3);
-- {'a': 1, 'b': 2, 'c': 3}

-- unnest struct into columns
SELECT unnest({'x': 1, 'y': 2, 'z': 3});
-- Returns columns x, y, z
```

---

## Map Functions

```sql
-- map: create a map
SELECT map([1, 2], ['a', 'b']);
-- {1=a, 2=b}

-- MAP literal
SELECT MAP {'key1': 'value1', 'key2': 'value2'};

-- map_from_entries: from list of key-value structs
SELECT map_from_entries([('a', 1), ('b', 2)]);

-- Element access
SELECT m['key1'] FROM (SELECT MAP {'key1': 10} AS m);

-- map_keys / map_values
SELECT map_keys(MAP {'a': 1, 'b': 2});     -- ['a', 'b']
SELECT map_values(MAP {'a': 1, 'b': 2});   -- [1, 2]

-- map_entries: convert back to list of structs
SELECT map_entries(MAP {'a': 1, 'b': 2});

-- cardinality: number of entries
SELECT cardinality(MAP {'a': 1, 'b': 2});  -- 2

-- map_contains_key (element_at returns NULL if missing)
SELECT element_at(MAP {'a': 1}, 'b');  -- NULL
```

---

## Spatial Functions (spatial Extension)

```sql
INSTALL spatial;
LOAD spatial;

-- Create geometry
SELECT ST_Point(40.7128, -74.0060) AS nyc;

-- Distance (in degrees for geographic, meters for projected)
SELECT ST_Distance(
    ST_Point(40.7128, -74.0060),
    ST_Point(34.0522, -118.2437)
);

-- Contains / Within
SELECT ST_Within(
    ST_Point(40.7128, -74.0060),
    ST_Buffer(ST_Point(40.71, -74.01), 0.01)
);

-- Read spatial files
SELECT * FROM ST_Read('boundaries.geojson');
SELECT * FROM ST_Read('parcels.shp');

-- Area and length
SELECT ST_Area(geom), ST_Length(geom) FROM spatial_table;

-- Transform coordinate reference systems
SELECT ST_Transform(geom, 'EPSG:4326', 'EPSG:3857') FROM my_table;
```

---

## Full-Text Search (fts Extension)

```sql
INSTALL fts;
LOAD fts;

-- Create full-text index
PRAGMA create_fts_index('documents', 'doc_id', 'title', 'body');

-- Search with BM25 scoring
SELECT doc_id, title, score
FROM (
    SELECT *, fts_main_documents.match_bm25(doc_id, 'search query') AS score
    FROM documents
)
WHERE score IS NOT NULL
ORDER BY score DESC;

-- Stemming
SELECT stem('running', 'english');
-- 'run'

-- Drop index
PRAGMA drop_fts_index('documents');
```

---

## Official Documentation

- All functions: <https://duckdb.org/docs/sql/functions/overview>
- Aggregate functions: <https://duckdb.org/docs/sql/functions/aggregates>
- Date functions: <https://duckdb.org/docs/sql/functions/date>
- String functions: <https://duckdb.org/docs/sql/functions/char>
- List functions: <https://duckdb.org/docs/sql/functions/list>
- Spatial extension: <https://duckdb.org/docs/extensions/spatial/overview>
- Full-text search: <https://duckdb.org/docs/extensions/full_text_search>
