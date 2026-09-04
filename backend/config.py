from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent
_CURVES_DIR = _BACKEND_DIR / "curves"


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

    # Forward-curve settlement snapshots for the ICE curves that aren't on Yahoo:
    # Brent + Gas Oil. Small daily-settle CSVs generated offline from the raw
    # Regime/data feeds by offline maintenance tooling and committed under
    # apps/api/curves/
    # (inside the Docker build context), so the deployed dashboard renders them even
    # though the raw feeds never leave local. WTI/Heating Oil/RBOB are live from
    # Yahoo contract months (see app/services/curve.py).
    brent_curve_csv: str = str(_CURVES_DIR / "brent_settle.csv")
    gasoil_curve_csv: str = str(_CURVES_DIR / "gasoil_settle.csv")
    curve_cache_ttl: float = 300.0

    # News — FinancialJuice public RSS feed (free, no key). Filtered to energy
    # headlines and sentiment-tagged locally (no paid API).
    news_feed_url: str = "https://www.financialjuice.com/feed.ashx?xy=rss"
    oilprice_feed_url: str = "https://oilprice.com/rss/main"
    news_cache_ttl: float = 60.0
    # Persistent scored-news memory (queue): keep the N most recent headlines, so
    # sentiment survives restarts, only NEW headlines are scored, and the feed
    # stays intact offline. File lives at apps/api/.news_store.json (gitignored).
    news_store_size: int = 40

    # Google Gemini — free-tier LLM sentiment scorer. Set via HORIZON_GEMINI_API_KEY
    # (get one at https://aistudio.google.com). Without it, scoring falls back to
    # the offline keyword lexicon automatically.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # Groq — free-tier, fast, OpenAI-compatible. Set via HORIZON_GROQ_API_KEY
    # (free key at https://console.groq.com/keys). Preferred over Gemini when set.
    # NOTE: the Groq/Gemini LLM scorer is no longer in the live news path (FinBERT
    # is the scorer). These stay for the swap-able boundary / future use.
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # FinBERT — local financial-sentiment model (ProsusAI/finbert) and the LIVE
    # polarity scorer for news. Runs on CPU via transformers (deps in
    # requirements.txt); no API key required. Set HORIZON_FINBERT_ENABLED=false to
    # fall back to the offline keyword lexicon.
    finbert_enabled: bool = True
    finbert_model: str = "ProsusAI/finbert"

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

    # Paper-trading / strategy engine. The engine lives in backend/strategy; it
    # reads the precomputed daily fair-value parquet cache and the 15-min bar DB.
    paper_strategy_dir: str = str(_BACKEND_DIR / "strategy")
    paper_cache_ttl: float = 15.0
    # Unified |z| thresholds (live engine == backtest). STOP widened to 2.5 to give
    # adverse room so normal intraday oscillation around the daily anchor doesn't
    # stop out; Z_EXTREME sits above STOP as the dislocation/no-entry guard.
    paper_entry: float = 1.0
    paper_exit: float = 0.5
    paper_stop: float = 2.5
    paper_z_extreme: float = 3.0

    # Live decision engine: "rolling" (price-only rolling-mean z, intraday-native,
    # completes round-trips on the 15-min bars) or "model" (regime daily fair value).
    # Rolling won the head-to-head on the live intraday window; the model fair value
    # / regime / OOD context is still computed and shown alongside as a sanity overlay.
    paper_engine: str = "rolling"
    paper_roll_lookback: int = 16   # 16 x 15-min bars = a round 4-hour window
    paper_roll_entry: float = 2.0
    paper_roll_exit: float = 0.5
    paper_roll_stop: float = 3.0
    paper_roll_z_extreme: float = 3.5

    # CORS — frontend dev origins
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
