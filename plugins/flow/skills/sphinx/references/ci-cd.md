
# Sphinx CI/CD Workflow

## Overview

Use this skill to build robust, automated documentation pipelines inside GitHub Actions. Complex documentation workflows often separate asset building templates (shell recorders like VHS) from core compilation nodes to keep static outputs fresh upon landing merges.

## Workflow Setup (`.github/workflows/docs.yml`)

### 1. Stage 1: Generate Dynamic Assets (VHS)

Run shell scripts mapping to animations BEFORE compiling Sphinx. This ensures the compilation stage receives fresh artifact caches.

```yaml
jobs:
  generate-demos:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install supporting components
        run: sudo apt-get install -y ffmpeg ttyd

      - name: Install VHS (via Go)
        uses: actions/setup-go@v5
        with:
          go-version: ">=1.21"

      - run: |
          go install github.com/charmbracelet/vhs@latest
          echo "$HOME/go/bin" >> $GITHUB_PATH

      - name: Compile Tape Scripts
        run: |
          for tape in docs/_tapes/*.tape; do
            vhs "$tape"
          done

      - name: Cache rendered visuals
        uses: actions/upload-artifact@v4
        with:
          name: demo-visuals
          path: docs/_static/demos/
```

### 2. Stage 2: Sphinx Compilation

Pull generated assets into standard template builds utilizing standard workflows.

```yaml
  build-docs:
    needs: generate-demos
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download visuals cache
        uses: actions/download-artifact@v4
        with:
          name: demo-visuals
          path: docs/_static/demos/

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Compile Static Docs
        run: |
            uv sync --all-extras --dev
            uv run sphinx-build -b html docs docs/_build/html

      - name: Upload build payload
        uses: actions/upload-pages-artifact@v3
        with:
          path: docs/_build/html/
```

### 3. Stage 3: Deploy

Push strictly from the compiled payload artifact sets:

```yaml
  deploy:
    needs: build-docs
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

## Best Practices

- **Separate Pre-renderers**: Keeps asset builder failures isolated from core page compilation cycles; easily skips tape generation if triggers specify visual frames didn't mutate.
- **Package Management with `uv`**: Avoid slow legacy standard setups; standard sync groups accelerate pipeline steps immensely when utilizing multi-threaded synchronization models.
- **Sandbox permissions**: Avoid Supply Chain vulnerabilities by loading script execution tools strictly inside isolated build components without mounting secret keys during demo rendering.
