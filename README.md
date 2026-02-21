# Persona Builder

FastAPI service for building, validating, and deploying AI persona configurations.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| POST | `/persona/assess` | Validate + confidence preview (no build) |
| POST | `/persona/build` | Full pipeline → write to disk |
| POST | `/persona/test` | Generate test scenarios only |
| POST | `/persona/deploy` | Full pipeline → write to disk + PostgreSQL |
| GET | `/persona/{name}` | Get latest version from disk |
| GET | `/persona/{name}/versions` | List all versions |
| GET | `/personas` | List all personas on disk |

## Pipeline

```
raw dict → normalize → validate → generate system prompt
  → generate OpenAI config + Claude config
  → generate test suite → score confidence
  → package delivery → persist (disk and/or DB)
```

All tools are deterministic with no network calls or AI reasoning.

## Setup

```bash
cp .env.example .env
# Edit .env with your DATABASE_URL
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8001
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `OPENAI_MODEL` | No | Model ID for generated OpenAI configs (default: `gpt-4o`) |
| `CLAUDE_MODEL` | No | Model ID for generated Claude configs (default: `claude-sonnet-4-20250514`) |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `PORT` | No | Server port (Railway injects automatically) |

## Deployment

Deployed on Railway via nixpacks. See `railway.toml` and `Procfile`.
