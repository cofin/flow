# Cloud Build Patterns

Production Cloud Build configurations for building and pushing container images to Artifact Registry.

## Basic Configuration

```yaml
timeout: "1800s"
options:
  machineType: "E2_HIGHCPU_8"
```

- **Machine type**: `E2_HIGHCPU_8` is recommended for Python builds with native extensions (e.g., grpcio, cryptography).
- **Timeout**: 30 minutes is a safe default for multi-stage Docker builds with frontend asset compilation.

## Build Pipeline Steps

### Step 0: Cache Warming

Pull the latest image to use as Docker build cache:

```yaml
steps:
  - id: "pull-latest"
    name: "gcr.io/cloud-builders/docker"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        docker pull ${_REGION_NAME}-docker.pkg.dev/${_PROJECT_ID}/my-artifacts/${_SERVICE_NAME}:latest || exit 0
```

The `|| exit 0` ensures the build continues even if no cached image exists (first build).

### Step 1: Build Runner Image

Build the main application image targeting a specific Dockerfile stage:

```yaml
  - id: "build-runner"
    name: "gcr.io/cloud-builders/docker"
    args:
      - "build"
      - "--target"
      - "runner"
      - "--cache-from"
      - "${_REGION_NAME}-docker.pkg.dev/${_PROJECT_ID}/my-artifacts/${_SERVICE_NAME}:latest"
      - "--build-arg"
      - "NPM_CONFIG_REGISTRY=${_NPM_CONFIG_REGISTRY}"
      - "--build-arg"
      - "PIP_INDEX_URL=${_PIP_INDEX_URL}"
      - "--build-arg"
      - "UV_INDEX_URL=${_UV_INDEX_URL}"
      - "-t"
      - "${_REGION_NAME}-docker.pkg.dev/${_PROJECT_ID}/my-artifacts/${_SERVICE_NAME}:${_BRANCH_NAME}-${_SHORT_SHA}"
      - "-t"
      - "${_REGION_NAME}-docker.pkg.dev/${_PROJECT_ID}/my-artifacts/${_SERVICE_NAME}:latest"
      - "--file"
      - "tools/deploy/docker/run/Dockerfile.distroless"
      - "."
```

### Step 2: Push Images

Push both the SHA-tagged and latest images to Artifact Registry:

```yaml
  - id: "push-latest"
    name: "gcr.io/cloud-builders/docker"
    args:
      - "push"
      - "${_REGION_NAME}-docker.pkg.dev/${_PROJECT_ID}/my-artifacts/${_SERVICE_NAME}:latest"

  - id: "push-sha"
    name: "gcr.io/cloud-builders/docker"
    args:
      - "push"
      - "${_REGION_NAME}-docker.pkg.dev/${_PROJECT_ID}/my-artifacts/${_SERVICE_NAME}:${_BRANCH_NAME}-${_SHORT_SHA}"
```

### Step 3: Build Worker Image (Optional)

Conditionally build a separate worker target for Cloud Run Jobs:

```yaml
  - id: "build-worker"
    name: "gcr.io/cloud-builders/docker"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        if [ "${_BUILD_WORKER}" = "true" ]; then
          docker build \
            --target worker \
            --cache-from ${_REGION_NAME}-docker.pkg.dev/${_PROJECT_ID}/my-artifacts/${_SERVICE_NAME}:latest \
            -t ${_REGION_NAME}-docker.pkg.dev/${_PROJECT_ID}/my-artifacts/${_SERVICE_NAME}-worker:${_BRANCH_NAME}-${_SHORT_SHA} \
            -t ${_REGION_NAME}-docker.pkg.dev/${_PROJECT_ID}/my-artifacts/${_SERVICE_NAME}-worker:latest \
            --file tools/deploy/docker/run/Dockerfile.distroless \
            .
          docker push ${_REGION_NAME}-docker.pkg.dev/${_PROJECT_ID}/my-artifacts/${_SERVICE_NAME}-worker:latest
          docker push ${_REGION_NAME}-docker.pkg.dev/${_PROJECT_ID}/my-artifacts/${_SERVICE_NAME}-worker:${_BRANCH_NAME}-${_SHORT_SHA}
        else
          echo "Skipping worker image build (_BUILD_WORKER != true)"
        fi
    waitFor: ["build-runner"]
```

## Tag Strategy

Two tags per image:

| Tag | Format | Purpose |
|-----|--------|---------|
| **latest** | `SERVICE:latest` | Cache source for subsequent builds, rolling deployments |
| **branch-sha** | `SERVICE:main-abc1234` | Immutable tag for traceability and rollbacks |

Built-in Cloud Build substitutions `_BRANCH_NAME` and `_SHORT_SHA` are used to construct the immutable tag.

## Substitution Variables

Define defaults that can be overridden per trigger:

```yaml
substitutions:
  _REGION_NAME: us-central1
  _BRANCH_NAME: master
  _NPM_CONFIG_REGISTRY: "https://registry.npmjs.org"
  _PIP_INDEX_URL: "https://pypi.org/simple"
  _UV_INDEX_URL: "https://pypi.org/simple"
  _BUILD_WORKER: "false"
```

Custom index substitutions (`_NPM_CONFIG_REGISTRY`, `_PIP_INDEX_URL`, `_UV_INDEX_URL`) support restricted environments with private package registries or mirrors.

## Artifact Registry Push Pattern

Images are pushed to regional Artifact Registry in the format:

```text
REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/IMAGE:TAG
```

Example:

```text
us-central1-docker.pkg.dev/my-project/my-artifacts/my-service:main-abc1234
```

## Multi-Target Builds

When a Dockerfile defines multiple targets (e.g., `runner` and `worker`), use `--target` to build each separately. The worker build can reuse layers from the runner build via `--cache-from` and `waitFor` dependencies.

## Key Patterns

- **Cache warming**: Always pull latest before building to maximize layer reuse
- **Conditional steps**: Use bash `if` blocks with substitution variables for optional steps
- **waitFor**: Control step ordering; worker builds should wait for runner to complete
- **Build args for registries**: Pass custom package index URLs as build args for air-gapped or mirrored environments
- **Separate worker images**: Use distinct image names (e.g., `service-worker`) for Cloud Run Jobs

## Official References

- <https://cloud.google.com/build/docs>
- <https://cloud.google.com/build/docs/configuring-builds/create-basic-configuration>
- <https://cloud.google.com/artifact-registry/docs/docker/pushing-and-pulling>
- <https://cloud.google.com/build/docs/configuring-builds/substitute-variable-values>
