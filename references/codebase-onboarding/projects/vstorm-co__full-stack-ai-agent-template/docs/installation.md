# Installation

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Install fastapi-fullstack

=== "uv (recommended)"

    ```bash
    uv tool install fastapi-fullstack
    ```

=== "pip"

    ```bash
    pip install fastapi-fullstack
    ```

=== "pipx"

    ```bash
    pipx install fastapi-fullstack
    ```

## Verify Installation

```bash
fastapi-fullstack --version
```

## Create Your First Project

```bash
# Interactive wizard (recommended)
fastapi-fullstack new

# Quick mode with options
fastapi-fullstack create my_app \
  --database postgresql \
  --auth jwt \
  --frontend nextjs

# Use presets
fastapi-fullstack create my_app --preset ai-agent
```

## Available Presets

| Preset | Description |
|--------|-------------|
| `--preset production` | Full production setup with Redis, Sentry, Kubernetes, Prometheus |
| `--preset ai-agent` | AI agent with WebSocket streaming and conversation persistence |
| `--minimal` | Minimal project with no extras |

## Project Dependencies

Generated projects use [uv](https://docs.astral.sh/uv/) for dependency management:

```bash
cd my_app/backend
make install  # Installs all dependencies
```

## Next Steps

- [Quick Start](guides/quick-start.md) - Set up your development environment
- [Configuration](guides/configuration.md) - Learn about configuration options
- [AI Agents](ai-agent.md) - Configure AI frameworks
