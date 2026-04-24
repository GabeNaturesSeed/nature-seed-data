.PHONY: install db-init db-migrate test lint audit research write publish

install:
	uv sync

db-init:
	uv run nspipe db init

db-migrate:
	uv run alembic upgrade head

test:
	uv run pytest -v

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

audit:
	uv run nspipe audit sync

research:
	uv run nspipe research keywords

write:
	uv run nspipe write brief

publish:
	uv run nspipe publish push
