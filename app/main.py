from fastapi import FastAPI

from app.routers import auth, users

app = FastAPI(title="Northlijn Server", version="0.1.0")

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/health")
def health_check() -> dict:
    """Plain liveness check — for Render's health checks, not app data."""
    return {"status": "ok"}
