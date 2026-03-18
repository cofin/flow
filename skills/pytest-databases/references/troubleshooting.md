# Troubleshooting

## Container Not Starting

1.  Ensure Docker/Podman is running.
2.  Check if port is already in use (plugin uses random ports, but conflicts happen).
3.  Verify image pull: `docker pull postgres:18`

## ARM Architecture (Apple Silicon)

Some databases need platform specification to run correctly.

```python
@pytest.fixture(scope="session")
def platform() -> str:
    return "linux/arm64"
```

## Xdist Worker Conflicts

If tests conflict in parallel execution, try increasing isolation.

```python
@pytest.fixture(scope="session")
def xdist_postgres_isolation_level() -> str:
    return "server"  # Use separate containers per worker
```
