# Contributing and development

## Development setup

```bash
UV_CACHE_DIR=/tmp/uv-cache uv venv .venv
UV_CACHE_DIR=/tmp/uv-cache uv pip install -p .venv/bin/python pytest pytest-httpx pytest-mock ruff
UV_CACHE_DIR=/tmp/uv-cache uv pip install -p .venv/bin/python -e .
```

## Run tests

```bash
.venv/bin/pytest -q
```

## Format code

```bash
.venv/bin/ruff format .
```

## Run CLI locally

```bash
.venv/bin/uniprot-insights --help
```

## Documentation workflow

```bash
UV_CACHE_DIR=/tmp/uv-cache uv pip install -p .venv/bin/python mkdocs
UV_CACHE_DIR=/tmp/uv-cache .venv/bin/mkdocs serve -a 0.0.0.0:8000
```

