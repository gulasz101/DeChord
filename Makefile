# Makefile
.PHONY: \
	install download-models test reset \
	backend frontend dev \
	portless-proxy-up portless-proxy-down portless-routes \
	backend-up backend-down backend-attach backend-status backend-logs \
	frontend-up frontend-down frontend-attach frontend-status frontend-logs \
	up down status logs

TMUX ?= tmux
BACKEND_SESSION ?= dechord-backend
FRONTEND_SESSION ?= dechord-frontend
BACKEND_CMD = cd "$(CURDIR)/backend" && portless api.dechord ./scripts/run-fastapi-portless.sh
FRONTEND_CMD = cd "$(CURDIR)/frontend" && portless dechord ./scripts/run-vite-portless.sh

install:
	cd backend && uv sync
	cd frontend && bun install

download-models:
	cd backend && uv run python -c "from demucs.api import Separator; Separator(model='htdemucs_ft'); print('htdemucs_ft downloaded'); Separator(model='htdemucs'); print('htdemucs downloaded')"
	@echo "Models downloaded successfully."

dev:
	@$(MAKE) up

backend:
	@$(MAKE) backend-up

frontend:
	@$(MAKE) frontend-up

test:
	cd backend && uv run pytest tests/ -v
	cd frontend && bun run test

reset:
	@$(MAKE) down
	rm -f backend/dechord.db backend/test_libsql.db backend/tmp_libsql.db
	rm -rf backend/uploads backend/stems backend/cache
	mkdir -p backend/uploads backend/stems
	@echo "Local backend state reset."

portless-proxy-up:
	@sudo PORTLESS_STATE_DIR=$(HOME)/.portless portless proxy start -p 80

portless-proxy-down:
	@sudo PORTLESS_STATE_DIR=$(HOME)/.portless portless proxy stop

portless-routes:
	@portless list

backend-up:
	@if $(TMUX) has-session -t "$(BACKEND_SESSION)" 2>/dev/null; then \
		echo "backend already running in tmux session: $(BACKEND_SESSION)"; \
	else \
		$(TMUX) new-session -d -s "$(BACKEND_SESSION)" '$(BACKEND_CMD)'; \
		echo "backend started in tmux session: $(BACKEND_SESSION)"; \
	fi

backend-down:
	@if $(TMUX) has-session -t "$(BACKEND_SESSION)" 2>/dev/null; then \
		$(TMUX) kill-session -t "$(BACKEND_SESSION)"; \
		echo "backend stopped: $(BACKEND_SESSION)"; \
	else \
		echo "backend session not running: $(BACKEND_SESSION)"; \
	fi

backend-attach:
	@$(TMUX) attach -t "$(BACKEND_SESSION)"

backend-status:
	@if $(TMUX) has-session -t "$(BACKEND_SESSION)" 2>/dev/null; then \
		echo "backend: running ($(BACKEND_SESSION))"; \
	else \
		echo "backend: stopped ($(BACKEND_SESSION))"; \
	fi

backend-logs:
	@if $(TMUX) has-session -t "$(BACKEND_SESSION)" 2>/dev/null; then \
		$(TMUX) capture-pane -p -t "$(BACKEND_SESSION)"; \
	else \
		echo "backend session not running: $(BACKEND_SESSION)"; \
		exit 1; \
	fi

frontend-up:
	@if $(TMUX) has-session -t "$(FRONTEND_SESSION)" 2>/dev/null; then \
		echo "frontend already running in tmux session: $(FRONTEND_SESSION)"; \
	else \
		$(TMUX) new-session -d -s "$(FRONTEND_SESSION)" '$(FRONTEND_CMD)'; \
		echo "frontend started in tmux session: $(FRONTEND_SESSION)"; \
	fi

frontend-down:
	@if $(TMUX) has-session -t "$(FRONTEND_SESSION)" 2>/dev/null; then \
		$(TMUX) kill-session -t "$(FRONTEND_SESSION)"; \
		echo "frontend stopped: $(FRONTEND_SESSION)"; \
	else \
		echo "frontend session not running: $(FRONTEND_SESSION)"; \
	fi

frontend-attach:
	@$(TMUX) attach -t "$(FRONTEND_SESSION)"

frontend-status:
	@if $(TMUX) has-session -t "$(FRONTEND_SESSION)" 2>/dev/null; then \
		echo "frontend: running ($(FRONTEND_SESSION))"; \
	else \
		echo "frontend: stopped ($(FRONTEND_SESSION))"; \
	fi

frontend-logs:
	@if $(TMUX) has-session -t "$(FRONTEND_SESSION)" 2>/dev/null; then \
		$(TMUX) capture-pane -p -t "$(FRONTEND_SESSION)"; \
	else \
		echo "frontend session not running: $(FRONTEND_SESSION)"; \
		exit 1; \
	fi

up:
	@$(MAKE) portless-proxy-up
	@$(MAKE) backend-up
	@$(MAKE) frontend-up

down:
	@$(MAKE) backend-down
	@$(MAKE) frontend-down

status:
	@$(MAKE) backend-status
	@$(MAKE) frontend-status

logs:
	@echo "=== backend logs ($(BACKEND_SESSION)) ==="
	-@$(MAKE) backend-logs
	@echo "=== frontend logs ($(FRONTEND_SESSION)) ==="
	-@$(MAKE) frontend-logs
