# Makefile
.PHONY: dev backend frontend install test

install:
	cd backend && uv sync
	cd frontend && bun install

dev:
	@echo "Starting backend and frontend..."
	@make backend & make frontend & wait

backend:
	cd backend && uv run fastapi dev app/main.py --port 8000

frontend:
	cd frontend && bun dev

test:
	cd backend && uv run pytest tests/ -v
	cd frontend && bun test
