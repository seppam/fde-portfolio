.PHONY: setup data up down dev test e2e eval eval-fuzzy lint odoo-key

setup:            ## install Python deps and the Playwright browser
	uv sync
	uv run playwright install chromium

data:             ## regenerate fictional master data and the 30-PO golden set
	uv run python scripts/gen_master.py
	uv run python scripts/gen_golden.py

up:               ## start Postgres (5434) and Mailpit (8026 web, 1026 smtp)
	docker compose up -d

down:
	docker compose stop

dev:              ## review app on http://localhost:8088
	set -a; . ./.env; set +a; DATABASE_URL=$${DATABASE_URL:-postgresql+psycopg://po:po@localhost:5434/po_agent} \
	uv run uvicorn po_agent.web.app:app --reload --port 8088 --app-dir src

test:             ## unit + API tests, offline, no LLM
	uv run pytest -m "not e2e and not llm and not odoo"

e2e:              ## browser tests (Playwright)
	uv run pytest tests/e2e -m e2e

eval:             ## score the real pipeline on the golden set (uses LLM APIs, cached)
	set -a; . ./.env; set +a; uv run python evals/run_eval.py --note "$(NOTE)"

eval-fuzzy:       ## same, without the LLM tie-break (fuzzy matching only)
	set -a; . ./.env; set +a; uv run python evals/run_eval.py --no-llm-match --note "fuzzy only"

lint:
	uv run ruff check src tests evals scripts
