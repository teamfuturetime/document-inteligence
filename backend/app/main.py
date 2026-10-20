"""Minimal API. Health reports liveness only, without loading AI services."""

from fastapi import FastAPI

app = FastAPI(title="AI-02 Document Intelligence", version="0.1.0")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Confirm that the backend can respond to HTTP requests."""
    return {"status": "ok"}
