# UV Migration Guide

This project has been migrated to use **uv** for faster Python package management.

## What Changed

### ✅ **Added**
- `pyproject.toml` - Modern Python project configuration
- `install-uv.sh` - Automated uv installation script
- `Makefile` - Enhanced with uv commands
- `apps/bench-cli/runtime/Dockerfile` - Updated to use uv for faster builds

### 🔄 **Updated**
- `env/dev.sh` - Enhanced with uv PATH and helpful commands
- `README.md` - Updated development instructions
- `requirements.txt` - Kept as backup (requirements.txt.bak)

## Quick Start

```bash
# Install uv and setup project
chmod +x install-uv.sh
./install-uv.sh

# Set environment
source env/dev.sh

# Start development
make dev
make migrate
make run-backend  # Terminal 1
make run-frontend # Terminal 2
```

## Benefits of UV

1. **🚀 10-100x faster** package installation
2. **🔒 Deterministic** dependency resolution with uv.lock
3. **📦 Better caching** and parallel downloads
4. **🛠️ Built-in** virtual environment management
5. **🔧 Drop-in replacement** for pip/pipenv/poetry

## Commands

| Task | Old Command | New Command |
|------|-------------|-------------|
| Install deps | `pip install -r requirements.txt` | `make dev` or `uv sync` |
| Run backend | `uvicorn apps.backend.main:app --reload` | `make run-backend` |
| Run tests | `pytest` | `make test` |
| Lint code | `ruff . && mypy .` | `make lint` |
| Run migrations | `alembic upgrade head` | `make migrate` |

## Docker Benefits

The Docker runtime now builds significantly faster using uv:
- Faster package resolution
- Better layer caching
- Parallel dependency installation

## Backward Compatibility

- Old `pip install -r requirements.txt` still works (using backup file)
- All existing scripts remain functional
- Can gradually adopt uv commands

## Next Steps

1. Run `./install-uv.sh` to get started
2. Use `make dev` for development setup
3. Enjoy faster dependency management! 🎉