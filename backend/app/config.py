from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = D:\Dashboard_FF (config.py -> app -> backend -> root).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration. Override via environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="HORIZON_", extra="ignore")

    # Yahoo Finance
    yahoo_base_url: str = "https://query1.finance.yahoo.com"
    yahoo_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    request_timeout: float = 15.0

    # Cache TTL (seconds) for quote snapshots
    cache_ttl: float = 20.0

    # EIA Open Data API (https://www.eia.gov/opendata/). Free key, set via
    # HORIZON_EIA_API_KEY. Weekly data, so a long cache TTL is fine.
    eia_api_key: str = ""
    eia_base_url: str = "https://api.eia.gov/v2"
    eia_cache_ttl: float = 3600.0

    # Forward-curve settlement CSVs (ICE). Brent ships with the repo; Gas Oil is
    # also ICE (not on Yahoo) so it reads from a CSV too — drop the file in and
    # it lights up. WTI/Heating Oil/RBOB curves come from Yahoo contract months.
    brent_curve_csv: str = str(_PROJECT_ROOT / "LCOSettle_2(in).csv")
    gasoil_curve_csv: str = str(_PROJECT_ROOT / "GasOilSettle.csv")
    curve_cache_ttl: float = 300.0

    # News — FinancialJuice public RSS feed (free, no key). Filtered to energy
    # headlines and sentiment-tagged locally (no paid API).
    news_feed_url: str = "https://www.financialjuice.com/feed.ashx?xy=rss"
    oilprice_feed_url: str = "https://oilprice.com/rss/main"
    news_cache_ttl: float = 60.0

    # CFTC Commitments of Traders — free Socrata API, no token. Disaggregated
    # Futures-Only dataset. Weekly data (released Fridays), so cache long.
    cftc_base_url: str = "https://publicreporting.cftc.gov"
    cftc_dataset: str = "72hh-3qpy"
    cftc_cache_ttl: float = 3600.0

    # Baker Hughes Rig Count — free Excel files (used with attribution per their
    # terms). We scrape the server-rendered page for the current file link, then
    # download + parse. NA weekly, International monthly. Fetched on demand.
    bh_base_url: str = "https://rigcount.bakerhughes.com/"
    bh_na_page: str = "na-rig-count"
    bh_intl_page: str = "intl-rig-count"

    # aisstream.io — free real-time AIS over WebSocket (free key, GitHub sign-in).
    # Set via HORIZON_AISSTREAM_API_KEY. Without it, the shipping consumer stays
    # off and the tanker map shows an "AIS offline" state.
    aisstream_api_key: str = ""
    aisstream_url: str = "wss://stream.aisstream.io/v0/stream"
    # Drop vessels not heard from in this many seconds.
    ais_vessel_ttl: float = 3600.0

    # CORS — frontend dev origins
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
