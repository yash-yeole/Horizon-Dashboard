from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that serializes to camelCase for a TS-friendly frontend."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Quote(CamelModel):
    id: str
    yahoo_symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    high: float | None = None
    low: float | None = None
    prev_close: float | None = None
    volume: int | None = None
    currency: str
    unit: str
    category: str
    sparkline: list[float] = []
    market_time: int | None = None
    stale: bool = False


class QuotesResponse(CamelModel):
    quotes: list[Quote]
    as_of: float  # epoch seconds when this snapshot was assembled


class HistoryPoint(CamelModel):
    time: int  # epoch seconds
    value: float


class HistoryResponse(CamelModel):
    id: str
    yahoo_symbol: str
    range: str
    interval: str
    points: list[HistoryPoint]


class CurvePoint(CamelModel):
    month: str  # M1, M2, ... (contract sequence)
    price: float  # latest settlement
    previous_price: float  # comparison snapshot settlement


class CurveResponse(CamelModel):
    id: str
    name: str
    currency: str
    unit: str
    as_of: str  # ISO date of the latest curve
    compare: str  # now | w1 | m1
    compare_date: str  # ISO date of the comparison snapshot
    points: list[CurvePoint]


class EiaPoint(CamelModel):
    period: str  # ISO week-ending date
    value: float | None = None


class EiaSeries(CamelModel):
    id: str  # frontend key: crude, cushing, gasoline, ...
    label: str
    unit: str
    latest: float | None = None
    previous: float | None = None
    change: float | None = None  # latest - previous (week-over-week)
    points: list[EiaPoint] = []


class EiaInventoryResponse(CamelModel):
    as_of: str  # most recent period across all series
    fetched_at: str = ""  # ISO timestamp of when we last pulled from EIA
    stale: bool = False
    series: list[EiaSeries]


class NewsItem(CamelModel):
    id: str
    headline: str
    summary: str = ""
    source: str = "FinancialJuice"
    timestamp: str = ""  # relative ("5m ago"), computed at fetch time
    published_at: int | None = None  # unix seconds, for client-side relative time
    category: str = "Macro"  # Crude | Products | Macro
    sentiment: str = "neutral"  # bullish | bearish | neutral
    importance: str = "medium"  # high | medium | low
    tags: list[str] = []
    link: str = ""


class NewsResponse(CamelModel):
    items: list[NewsItem]
    as_of: float
    stale: bool = False


class CftcPoint(CamelModel):
    date: str  # report date (Tuesday), ISO
    value: int  # managed-money net position


class CftcContract(CamelModel):
    id: str
    name: str
    code: str
    report_date: str
    open_interest: int = 0
    mm_long: int = 0
    mm_short: int = 0
    mm_net: int = 0
    mm_net_change: int = 0  # week-over-week change in net
    pm_long: int = 0  # producer / merchant (commercials)
    pm_short: int = 0
    swap_long: int = 0
    swap_short: int = 0
    other_long: int = 0
    other_short: int = 0
    net_history: list[CftcPoint] = []


class CftcResponse(CamelModel):
    as_of: str  # latest report date
    stale: bool = False
    contracts: list[CftcContract]


class RigItem(CamelModel):
    label: str
    value: float
    change: float | None = None  # week-over-week (NA) or month-over-month (intl)
    year_ago: float | None = None


class RigGroup(CamelModel):
    name: str  # e.g. "Oil vs Gas", "Trajectory", "Basin", "By Region"
    items: list[RigItem]


class RigSeriesPoint(CamelModel):
    date: str  # YYYY-MM
    value: float


class RigSeries(CamelModel):
    name: str
    points: list[RigSeriesPoint]


class LeadLagPoint(CamelModel):
    lag: int       # in bars
    corr: float


class LeadLagPair(CamelModel):
    id: str
    name: str
    best_lag: int            # bars; >0 => base leads other, <0 => other leads base
    best_lag_minutes: int
    best_corr: float
    same_corr: float         # contemporaneous correlation (lag 0)
    leader: str              # "base" | "other" | "sync"
    ccf: list[LeadLagPoint]


class LeadLagResponse(CamelModel):
    base: str
    base_name: str
    timeframe: str
    interval: str
    bar_minutes: int
    samples: int             # aligned sample size used
    as_of: float
    pairs: list[LeadLagPair]


class RigCountResponse(CamelModel):
    na_report_date: str = ""
    ww_report_date: str = ""
    fetched_at: str = ""
    stale: bool = False
    na_summary: list[RigItem] = []   # United States, Canada, North America
    na_groups: list[RigGroup] = []   # Oil vs Gas, Trajectory, Basin, Location
    intl_summary: list[RigItem] = []  # International, Worldwide
    intl_regions: list[RigItem] = []  # by region
    ww_history: list[RigSeries] = []  # Worldwide + regions, monthly
