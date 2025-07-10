#!/bin/bash
# Install uv if not present

if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "uv is already installed"
fi

echo "Setting up project with uv..."
cd /Users/uenin/bab_l_s
uv sync

echo "uv setup complete!"
echo "You can now use:"
echo "  make dev          - Setup development environment"
echo "  make run-backend  - Start backend server"
echo "  make run-frontend - Start frontend server"