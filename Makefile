# Chicago Crimes Analytics — atajos del proyecto (Sprint 1).
#
# Uso local (Linux/macOS o Git Bash en Windows):
#   make up                 # levanta postgres + n8n (desarrollo)
#   make migrate            # aplica database/migrations/*.sql en orden
#   make views              # aplica database/views/*.sql (vistas analíticas)
#   make test-up            # levanta la DB de pruebas (puerto 5433)
#   make test-integration   # pytest contra la DB de pruebas
#   make lint               # ruff (requiere requirements-dev.txt)
#
# En PowerShell sin `make`, los comandos equivalentes están en
# docs/database.md (§2-§3, §9) y docs/testing.md (§4).

.DEFAULT_GOAL := help

.PHONY: help up down migrate seed load-warehouse views test-up test-down test-unit test-integration lint

help:
	@echo "Targets: up down migrate seed load-warehouse views test-up test-down test-unit test-integration lint"

up:
	docker compose up -d

down:
	docker compose down

migrate:
	for f in database/migrations/*.sql; do \
	  docker compose exec -T postgres psql -U postgres -d chicago_crimes -f "/database/$${f#database/}"; \
	done

seed:
	for f in database/seeds/*.sql; do \
	  docker compose exec -T postgres psql -U postgres -d chicago_crimes -f "/database/$${f#database/}"; \
	done

load-warehouse:
	docker compose exec -T postgres psql -U postgres -d chicago_crimes \
	  -f /database/functions/load_warehouse.sql \
	  -c "SELECT warehouse.load_warehouse();"

views:
	for f in database/views/*.sql; do \
	  docker compose exec -T postgres psql -U postgres -d chicago_crimes -f "/database/$${f#database/}"; \
	done

test-up:
	docker compose -f docker-compose.test.yml up -d

test-down:
	docker compose -f docker-compose.test.yml down

test-unit:
	pytest python/tests/unit -v

test-integration:
	pytest python/tests/integration -v

lint:
	ruff check python
