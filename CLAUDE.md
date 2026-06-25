# CLAUDE.md — sf-change-ledger

Flask app + MCP server that tracks SAP SuccessFactors configuration changes by comparing exports over time.

## Structure
- `app.py` — Flask app entry point
- `core/` — ledger logic (diff, storage, reporting)
- `tests/` — pytest tests

## Commands
- Tests: `python -m pytest tests/ -q`
- Lint: `ruff check .`
- Push: `git push origin main` (rebased)

## Rules
- Don't modify the diff algorithm or storage schema without asking
- Security patches (defusedxml, CSRF, CORS) were carefully added — don't revert
