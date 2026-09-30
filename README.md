# Northlijn Server

Phase 1 of Northlijn's account system: signup, login, JWT access + refresh
tokens, and account deletion. Nothing else yet — no data syncs here. See
the iOS project's memory notes for the full phased plan (Phase 2 = sync,
Phase 3 = subscriptions).

## Local development

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then edit DATABASE_URL and JWT_SECRET_KEY
```

Generate a real secret for `.env`:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

You need a real Postgres for local dev (matches production exactly):
```bash
# DATABASE_URL in .env, e.g.:
# postgresql+psycopg://northlijn:northlijn@localhost:5432/northlijn
./.venv/bin/alembic upgrade head
./.venv/bin/uvicorn app.main:app --reload
```

No local Postgres? The test suite runs against in-memory SQLite instead
(see `tests/conftest.py`) and needs no setup:
```bash
./.venv/bin/python -m pytest tests/ -v
```

## Deploying to Render

1. Push this directory to its own GitHub repo.
2. Render → New → Web Service → connect the repo. Build command:
   `pip install -r requirements.txt`. Start command:
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Render → New → PostgreSQL (smallest tier). Copy its internal
   connection string into the web service's `DATABASE_URL` environment
   variable.
4. Set `JWT_SECRET_KEY` as a Render environment variable — generate a new
   one the same way as above; never reuse the local dev secret.
5. Run `alembic upgrade head` against the production database once (Render
   → Shell tab on the web service, or a one-off Job) before the first
   request hits `/auth/signup`.
6. Confirm `GET /health` returns `{"status": "ok"}` before pointing the
   iOS app at it.

## Endpoints

| Method | Path            | Auth required | Notes |
|--------|-----------------|---------------|-------|
| POST   | `/auth/signup`  | no            | 201 + token pair, or 409 if email taken |
| POST   | `/auth/login`   | no            | 200 + token pair, or 401 (generic message) |
| POST   | `/auth/refresh` | no (refresh token in body) | Rotates the refresh token |
| POST   | `/auth/logout`  | no (refresh token in body) | Idempotent |
| GET    | `/users/me`     | yes (Bearer access token) | |
| DELETE | `/users/me`     | yes (Bearer access token) | Required by Apple Guideline 5.1.1(v) |
| GET    | `/health`       | no            | Liveness check for Render |
