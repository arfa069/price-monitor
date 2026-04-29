# Repository Guidelines

## Project Structure & Module Organization
`backend/app/` contains the FastAPI backend: `main.py` for app startup, `routers/` for HTTP endpoints, `services/` for crawl and notification logic, `models/` and `schemas/` for persistence and validation, and `platforms/` for Taobao/JD/Amazon adapters. `backend/alembic/` and `backend/alembic.ini` hold database migrations. `frontend/` is the Vite + React client, with source under `frontend/src/`. Tests live in `backend/tests/`; screenshots and manual QA artifacts are stored under `backend/tests/screenshots/` and `backend/tests/*.md`.

## Build, Test, and Development Commands
- `cd backend && uvicorn app.main:app` starts the backend locally. On Windows, do not use `--reload`.
- `cd backend && alembic upgrade head` applies database migrations.
- `cd backend && pytest` runs the Python test suite from `backend/tests/`.
- `cd backend && ruff check .` runs Python linting.
- `cd frontend && npm run dev` starts the UI on port `3000`.
- `cd frontend && npm run build` type-checks and builds the frontend.
- `cd frontend && npm run lint` runs ESLint.

## Coding Style & Naming Conventions
Use Python 3.11+, 4-space indentation, and keep imports sorted for Ruff (`E`, `F`, `I`, `N`, `W`, `UP`). Prefer explicit async/await code and keep business logic in services rather than routers. Name backend files by domain, such as `crawl.py`, `notification.py`, or `jd.py`. In the frontend, use TypeScript, PascalCase for components, camelCase for hooks and helpers, and colocate feature code under `frontend/src/components/` or `frontend/src/pages/`.

## Testing Guidelines
Pytest is the standard test framework. Tests follow `test_*.py` naming and belong in `backend/tests/`. Prefer focused unit tests for adapters and services, plus API tests for endpoints and pagination. When changing crawl, scheduler, or notification behavior, add coverage for failure and edge cases, not just happy paths. Use `cd backend && coverage run -m pytest` and `cd backend && coverage report` when validating broader changes.

## Commit & Pull Request Guidelines
Recent commits use short Conventional Commit style messages such as `feat(scope): ...`, `fix(scope): ...`, and occasional verification tags like `[verified]`. Keep messages imperative and scoped when practical. Pull requests should describe the change, list verification performed, and include screenshots for visible frontend updates. Link related issues or notes when applicable.

## Security & Configuration Tips
Keep secrets in `.env` at the project root; never hardcode database, Redis, Feishu, or browser/CDP credentials. Review `README.md` and `ARCHITECTURE.md` before changing config, scheduling, or crawl behavior, because the backend runs crawls in-process inside FastAPI rather than through a separate worker.

## RTK
@C:\Users\arfac\.codex\RTK.md
