# ui_automation

## Specification

See `docs/spec.md` for the full project specification.

## Quick Start

```bash
pip install -e .
uvicorn ui_automation.api:app --reload
```

## API

- `GET /health`: health check
- `POST /run`: execute a validated DSL plan through orchestrator/compiler/executor flow
