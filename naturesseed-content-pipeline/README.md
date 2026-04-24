# Nature's Seed Content Pipeline

Agentic content pipeline: audit, research, write, publish.

## Setup

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
make install

# Initialize the database
make db-init

# Run migrations (after schema changes)
make db-migrate
```

## CLI

```bash
nspipe --help          # List all commands
nspipe db init         # Create database tables
nspipe audit sync      # Sync content inventory from WordPress
nspipe research keywords  # Discover keyword candidates
nspipe write brief     # Generate content briefs
nspipe publish push    # Push to WordPress
```

## Development

```bash
make test              # Run tests
make lint              # Ruff check + format
pre-commit install     # Install git hooks
```

## Project Structure

```
src/naturesseed_pipeline/
  config.py            # pydantic-settings (.env)
  cli.py               # typer CLI (nspipe)
  logging_config.py    # structlog
  db/                  # SQLAlchemy models + Alembic
  agents/              # Agent definitions
  integrations/        # WordPress, keyword APIs, analytics
  pipelines/           # Orchestration per stage
```
