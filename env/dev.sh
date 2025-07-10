#!/bin/bash
# Development environment variables

export DATABASE_URL=sqlite:///./local.db
export REDIS_URL=redis://localhost:6379/0
export JWT_SECRET=devsecret
export BENCH_API_URL=http://localhost:8000
export PYTHONPATH="$PWD"

# Add uv to PATH if it exists in user's home
if [ -d "$HOME/.local/bin" ]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Development environment variables set:"
echo "DATABASE_URL=$DATABASE_URL"
echo "REDIS_URL=$REDIS_URL" 
echo "BENCH_API_URL=$BENCH_API_URL"
echo "PYTHONPATH=$PYTHONPATH"
echo ""
echo "Note: This setup uses SQLite instead of PostgreSQL and assumes Redis is not running"
echo "The backend will work with SQLite for development purposes"
echo ""
echo "Quick commands:"
echo "  make dev          - Setup development environment"
echo "  make run-backend  - Start backend server"
echo "  make run-frontend - Start frontend server"
echo "  make migrate      - Run database migrations"
echo "  make test         - Run tests"
echo "  make lint         - Run linting"