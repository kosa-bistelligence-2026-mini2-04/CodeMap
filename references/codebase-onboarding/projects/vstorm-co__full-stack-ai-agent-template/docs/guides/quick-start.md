# Quick Start

Get your AI application running in 5 minutes.

## 1. Create a Project

```bash
# Interactive wizard (recommended)
fastapi-fullstack new

# Or use the AI agent preset
fastapi-fullstack create my_app --preset ai-agent
```

## 2. Install Dependencies

```bash
cd my_app
make install
```

!!! note "Windows Users"
    The `make` command requires GNU Make. Install via [Chocolatey](https://chocolatey.org/) (`choco install make`), use WSL, or run commands manually from the Makefile.

## 3. Start the Database

```bash
# PostgreSQL with Docker
make docker-db
```

## 4. Run Migrations

```bash
# Create initial migration
make db-migrate
# Enter message: "Initial migration"

# Apply migrations
make db-upgrade
```

## 5. Create Admin User

```bash
make create-admin
# Enter email and password when prompted
```

## 6. Start the Backend

```bash
make run
```

## 7. Start the Frontend

Open a new terminal:

```bash
cd frontend
bun install
bun dev
```

## Access Your Application

| Service | URL |
|---------|-----|
| **API** | http://localhost:8000 |
| **API Docs** | http://localhost:8000/docs |
| **Admin Panel** | http://localhost:8000/admin |
| **Frontend** | http://localhost:3000 |

## Using Docker

Run everything in containers:

```bash
make docker-up       # Start backend + database
make docker-frontend # Start frontend
```

## Project CLI

Each generated project has a CLI:

```bash
cd backend

# Server commands
uv run my_app server run --reload

# Database commands
uv run my_app db migrate -m "Add users"
uv run my_app db upgrade

# User commands
uv run my_app user create-admin
```

## Next Steps

- [Configuration](configuration.md) - Customize your project
- [AI Agents](../ai-agent.md) - Set up AI frameworks
- [Deployment](../deployment.md) - Deploy to production
