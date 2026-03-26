# SQLSpec Observability & Tracing

## Logging Framework

SQLSpec emits structured log records following OpenTelemetry semantic conventions to aid distributed systems diagnosis.

### Common Event Fields

- `timestamp`, `level`, `logger`, `message` (static name)
- `db.system`, `db.operation`, `db.statement` (truncated if needed)
- `duration_ms`, `rows_affected`

### Configuration

```python
from sqlspec.observability import ObservabilityConfig, LoggingConfig

ObservabilityConfig(
    logging=LoggingConfig(
        include_sql_hash=True,
        sql_truncation_length=2000,
        include_trace_context=True,
    )
)
```

---

## Correlation Middleware

Extracts trace headers across HTTP environments (Starlette, FastAPI, Flask).

### Supported Headers (Priority order)

1. `CorrelationExtractor` configured `correlation_header`
2. `traceparent` (W3C Trace Context)
3. `x-cloud-trace-context` (GCP)
4. `x-request-id`

### Generic Extraction Pattern

```python
from sqlspec.core import CorrelationExtractor

extractor = CorrelationExtractor(primary_header="x-request-id")
correlation_id = extractor.extract(lambda h: request.headers.get(h))
```

---

## Sampling Diagnostics

Control volume rates using bounded rates and clamps.

```python
from sqlspec.observability import SamplingConfig

config = SamplingConfig(
    sample_rate=0.1,                 # Sample 10% of requests
    force_sample_on_error=True,     # Always sample errors
    deterministic=True,              # Stable across replicas
)
```
