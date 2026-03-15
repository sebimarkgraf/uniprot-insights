# AGENTS Instructions

This project uses a local `uv` virtual environment for development and test execution.

## Environment setup

Use these commands from the repository root:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv venv .venv
UV_CACHE_DIR=/tmp/uv-cache uv pip install -p .venv/bin/python pytest pytest-httpx pytest-mock
UV_CACHE_DIR=/tmp/uv-cache uv pip install -p .venv/bin/python -e .
```

If `.venv` exists but is not a valid virtual environment:

```bash
rm -rf .venv
UV_CACHE_DIR=/tmp/uv-cache uv venv .venv
```

## Running tests

```bash
.venv/bin/pytest -q
```

After any code, documentation, or configuration change, run the test suite with `.venv/bin/pytest -q` before wrapping up that change.

The expected current baseline is:

```text
11 passed
```

## Notes

- `UV_CACHE_DIR=/tmp/uv-cache` is used to avoid permission issues with default cache locations.
- Python package dependencies should be installed into `.venv` before test execution.
