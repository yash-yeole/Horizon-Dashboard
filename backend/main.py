"""HORIZON market data API.

Run from this directory with:
    uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routes import router
from services import shipping

app = FastAPI(
    title="HORIZON Market Data API",
    description="Thin proxy + cache over public energy-market data sources.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def _startup() -> None:
    # Launch the AIS WebSocket consumer if a key is configured.
    shipping.start()


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "horizon-market-data"}
