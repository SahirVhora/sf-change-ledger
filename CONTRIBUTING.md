# Contributing

Contributions that improve parser coverage, risk rules, reporting, tests, or
accessibility are welcome.

## Development Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

Run the web application:

```bash
PYTHONPATH=src python3 web/app.py
```

## Pull Requests

1. Create a focused branch.
2. Keep parser changes isolated from unrelated refactoring.
3. Add anonymised fixtures and tests for every new export shape.
4. Run `ruff check .` and `pytest -q`.
5. Update the README or architecture document when behaviour changes.

Do not commit tenant credentials, employee data, client exports, generated
reports, or local environment files.

## Parser Contract

Every parser must emit stable `ConfigObject` records with:

- a meaningful `kind`
- a deterministic `object_id`
- a readable `label`
- normalised semantic `properties`
- the source file path

Formatting, timestamps, and export-order changes must not create false
configuration findings.
