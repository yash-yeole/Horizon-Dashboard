from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import (
    calendar, cftc, curve, eia, leadlag, news, paper, quotes, release_impact, rigcount, shipping,
)
from .services import shipping as shipping_service

app = FastAPI(
    title="HORIZON Market Data API",
    description="Thin proxy + cache over Yahoo Finance for the HORIZON energy terminal.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Allow any Hugging Face Space subdomain (the deployed frontend lives at
    # https://<owner>-<space>.hf.space) so the browser doesn't block cross-origin
    # API calls. Local dev origins stay in settings.cors_origins above.
    allow_origin_regex=r"https://[a-z0-9-]+\.hf\.space",
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(calendar.router)
app.include_router(quotes.router)
app.include_router(curve.router)
app.include_router(eia.router)
app.include_router(news.router)
app.include_router(cftc.router)
app.include_router(rigcount.router)
app.include_router(leadlag.router)
app.include_router(shipping.router)
app.include_router(paper.router)
app.include_router(release_impact.router)


@app.on_event("startup")
async def _startup() -> None:
    # Launch the AIS WebSocket consumer if a key is configured.
    shipping_service.start()


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "horizon-market-data"}
