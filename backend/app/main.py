from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import cftc, curve, eia, news, quotes, rigcount

app = FastAPI(
    title="HORIZON Market Data API",
    description="Thin proxy + cache over Yahoo Finance for the HORIZON energy terminal.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(quotes.router)
app.include_router(curve.router)
app.include_router(eia.router)
app.include_router(news.router)
app.include_router(cftc.router)
app.include_router(rigcount.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "horizon-market-data"}
