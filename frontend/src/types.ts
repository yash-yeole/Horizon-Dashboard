// Shared TypeScript types for the HORIZON frontend.

// ---------------------------------------------------------------- UI / market

// Market data types
export interface PricePoint {
  time: string;
  value: number;
  volume?: number;
}

export interface Commodity {
  id: string;
  name: string;
  symbol: string;
  price: number;
  change: number;
  changePct: number;
  high: number;
  low: number;
  volume: string;
  unit: string;
  currency: string;
  category: CommodityCategory;
  sparkline: number[];
}

export type CommodityCategory =
  | 'crude'
  | 'products'
  | 'gas'
  | 'lng'
  | 'power'
  | 'macro'
  | 'freight';

export interface NewsItem {
  id: string;
  headline: string;
  summary: string;
  source: string;
  timestamp: string;
  category: string;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  importance: 'high' | 'medium' | 'low';
  tags: string[];
  impact?: number;
  confidence?: number;
  themePrimary?: string;
  themesSecondary?: string[];
  productDivergence?: boolean;
  kind?: 'event' | 'forecast' | 'opinion';
  eventKey?: string;
}

export interface InventoryData {
  week: string;
  crude: number;
  gasoline: number;
  distillate: number;
  propane: number;
  total: number;
}

export interface FreightRate {
  route: string;
  vessel: string;
  rate: number;
  change: number;
  changePct: number;
  unit: string;
}

export interface WeatherStation {
  city: string;
  region: string;
  temp: number;
  anomaly: number;
  hdd: number;
  cdd: number;
  forecast: string;
}

export interface AlertItem {
  id: string;
  title: string;
  message: string;
  type: 'price' | 'news' | 'weather' | 'inventory' | 'freight';
  severity: 'critical' | 'warning' | 'info';
  timestamp: string;
  read: boolean;
  commodity?: string;
}

export interface SpreadData {
  name: string;
  value: number;
  change: number;
  history: number[];
}

export interface CurvePoint {
  month: string;
  price: number;
  previousPrice: number;
}

export interface CorrelationEntry {
  asset: string;
  values: Record<string, number>;
}

export interface NavItem {
  id: string;
  label: string;
  icon: string;
  path: string;
  badge?: number;
}

// ------------------------------------------------- API (FastAPI response models)

// Mirrors the FastAPI backend response models (camelCase via Pydantic alias).

export interface ApiQuote {
  id: string;
  yahooSymbol: string;
  name: string;
  price: number;
  change: number;
  changePct: number;
  high: number | null;
  low: number | null;
  prevClose: number | null;
  volume: number | null;
  currency: string;
  unit: string;
  category: string;
  sparkline: number[];
  marketTime: number | null;
  stale: boolean;
}

export interface QuotesResponse {
  quotes: ApiQuote[];
  asOf: number;
}

export interface HistoryPoint {
  time: number;
  value: number;
}

export interface HistoryResponse {
  id: string;
  yahooSymbol: string;
  range: string;
  interval: string;
  points: HistoryPoint[];
}

export type QuoteGroup = 'core' | 'macro' | 'products' | 'all';

export type CurveCompare = 'now' | 'w1' | 'm1';


export interface CurveResponse {
  id: string;
  name: string;
  currency: string;
  unit: string;
  asOf: string;
  compare: CurveCompare;
  compareDate: string;
  points: CurvePoint[];
}

export interface CurveStructurePoint {
  date: string;
  value: number;
}

export interface CurveStructureSeries {
  key: string;
  label: string;
  points: CurveStructurePoint[];
}

export interface CurveStructureResponse {
  id: string;
  name: string;
  currency: string;
  unit: string;
  asOf: string;
  spreads: CurveStructureSeries[];
  flys: CurveStructureSeries[];
}

export interface EiaPoint {
  period: string;
  value: number | null;
}

export interface EiaSeries {
  id: string;
  label: string;
  unit: string;
  latest: number | null;
  previous: number | null;
  change: number | null;
  points: EiaPoint[];
}

export interface EiaInventoryResponse {
  asOf: string;
  fetchedAt: string;
  stale: boolean;
  series: EiaSeries[];
}

export interface NewsApiItem {
  id: string;
  headline: string;
  summary: string;
  source: string;
  timestamp: string;
  publishedAt: number | null;
  category: string;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  importance: 'high' | 'medium' | 'low';
  tags: string[];
  link: string;
  impact: number;
  confidence: number;
  themePrimary: string;
  themesSecondary: string[];
  productDivergence: boolean;
  kind: 'event' | 'forecast' | 'opinion';
  eventKey: string;
}

export interface NewsResponse {
  items: NewsApiItem[];
  asOf: number;
  stale: boolean;
}

export interface CftcPoint {
  date: string;
  value: number;
}

export interface CftcContract {
  id: string;
  name: string;
  code: string;
  reportDate: string;
  openInterest: number;
  mmLong: number;
  mmShort: number;
  mmNet: number;
  mmNetChange: number;
  pmLong: number;
  pmShort: number;
  swapLong: number;
  swapShort: number;
  otherLong: number;
  otherShort: number;
  netHistory: CftcPoint[];
}

export interface CftcResponse {
  asOf: string;
  stale: boolean;
  contracts: CftcContract[];
}

export interface RigItem {
  label: string;
  value: number;
  change: number | null;
  yearAgo: number | null;
}

export interface RigGroup {
  name: string;
  items: RigItem[];
}

export interface RigSeries {
  name: string;
  points: { date: string; value: number }[];
}

export interface LeadLagPoint {
  lag: number;
  corr: number;
}

export interface LeadLagPair {
  id: string;
  name: string;
  bestLag: number;
  bestLagMinutes: number;
  bestCorr: number;
  sameCorr: number;
  leader: 'base' | 'other' | 'sync';
  ccf: LeadLagPoint[];
}

export interface LeadLagResponse {
  base: string;
  baseName: string;
  timeframe: string;
  interval: string;
  barMinutes: number;
  samples: number;
  asOf: number;
  pairs: LeadLagPair[];
}

export interface RigCountResponse {
  naReportDate: string;
  wwReportDate: string;
  fetchedAt: string;
  stale: boolean;
  naSummary: RigItem[];
  naGroups: RigGroup[];
  intlSummary: RigItem[];
  intlRegions: RigItem[];
  wwHistory: RigSeries[];
}

export interface ShippingStatus {
  hasKey: boolean;
  connected: boolean;
  vesselCount: number;
}

export interface AisVessel {
  mmsi: number;
  name: string;
  klass: string;
  lat: number;
  lon: number;
  sog: number | null;
  cog: number | null;
  heading: number | null;
  destination: string;
  lastSeen: number;
}

export interface VesselsResponse {
  status: ShippingStatus;
  vessels: AisVessel[];
}

export interface ChokepointStat {
  name: string;
  count: number;
  avg7d: number | null;
  avg30d: number | null;
  baseline: number;
  deviation: number;
  status: 'Normal' | 'Elevated' | 'Congested';
}

export interface ChokepointsResponse {
  status: ShippingStatus;
  chokepoints: ChokepointStat[];
}

export interface CalendarEvent {
  date: string;       // YYYY-MM-DD
  timeEt: string;     // "10:30" or "" if time not fixed
  title: string;
  category: string;   // EIA | CFTC | OPEC | IEA | BakerHughes
  importance: 'high' | 'medium' | 'low';
  description: string;
  isDelayed: boolean;
}

// ── Inventory-release impact ──
export interface ReleaseScenario {
  actual: number;
  surpriseVsConsensus: number;
  surpriseVsOurs: number;
  lean: 'bullish' | 'neutral' | 'bearish';
  label: string;
}

export interface DriverFactor {
  name: string;
  stdBeta: number;
  pValue: number;
  significant: boolean;
}

export interface NewsTheme {
  theme: string;
  count: number;
}

export interface ForecastDriver {
  label: string;
  value: number;
  unit: string;
}

export interface InventoryForecast {
  targetWeekEnding: string;
  asOfWeek: string;
  predictedChange: number;
  sd: number;
  r2: number;
  oosR2: number;
  drivers: ForecastDriver[];
  note: string;
}

export interface ProductEffect {
  product: string;
  channel: string;
  beta: number;
  pValue: number;
  significant: boolean;
  spread: string;
  lean: 'bullish' | 'neutral' | 'bearish';
  note: string;
}

export interface ReleaseImpactResponse {
  series: string;
  instrument: string;
  nextReleaseDate: string;
  timeEt: string;
  daysUntil: number;
  isDelayed: boolean;
  consensus: number | null;
  previous: number | null;
  ourForecast: InventoryForecast | null;
  ourSurpriseVsConsensus: number | null;
  bias: 'bullish' | 'bearish' | 'neutral';
  confidence: 'low' | 'medium' | 'high';
  headline: string;
  reasoning: string;
  scenarios: ReleaseScenario[];
  inventoryBeta: number;
  topFactors: DriverFactor[];
  spreadFocus: string;
  productEffects: ProductEffect[];
  newsThemes: NewsTheme[];
  headlines: string[];
  framework: string;
  asOf: number;
  stale: boolean;
}

// ---------------------------------------------------------- paper trading

export interface PaperThresholds {
  entry: number;
  exit: number;
  stop: number;
  z_extreme: number;
}

export interface PaperSignal {
  action: string;        // BUY | SELL | NO_TRADE | ...
  direction: string | null;
  planned_entry: number | null;
  target: number | null;
  stop: number | null;
  rationale: string | null;
}

export interface PaperOpenPosition {
  direction: string;
  size: number;
  entry_ts: string;
  entry_price: number | null;
  target: number | null;
  stop: number | null;
  current_price: number | null;
  current_z: number | null;
  unrealized_pnl: number | null;
  regime: string | null;
  confidence: string | null;
  rationale: string | null;
}

export interface PaperTrade {
  direction: string;
  regime: string | null;
  confidence: string | null;
  entry_ts: string;
  entry_price: number | null;
  exit_ts: string;
  exit_price: number | null;
  exit_reason: string;
  target: number | null;
  stop: number | null;
  net_pnl: number | null;
  win: boolean;
  hold_bars: number | null;
}

export interface PaperZPoint {
  t: string;
  z: number | null;
  spread: number | null;
}

export interface PaperEquityPoint {
  t: string;
  equity: number | null;
}

export interface PaperByRegime {
  regime: string;
  n: number;
  win_rate: number | null;
  net_pnl: number | null;
  avg_pnl: number | null;
}

export interface PaperStructure {
  key: string;
  label: string;
  instrument?: string;
  structure?: string;
  legs?: string | null;
  bars?: number;
  as_of?: string;
  regime?: string | null;
  confidence?: string | null;
  ood?: boolean | null;
  near_boundary?: boolean | null;
  watch_only?: boolean;
  fair_value?: number | null;
  fv_drift?: number | null;
  fair_value_fundamental?: number | null;
  resid_std?: number | null;
  live_spread?: number | null;
  live_z?: number | null;
  rich_cheap?: string;
  engine?: string;                  // "rolling" | "model" — the live decision engine
  roll_lookback?: number | null;    // rolling-mean window length (bars)
  roll_anchor?: number | null;      // rolling-mean anchor (the trading fair value)
  roll_std?: number | null;         // rolling std (z denominator)
  thresholds?: PaperThresholds;
  signal?: PaperSignal | null;
  open_position?: PaperOpenPosition | null;
  z_series?: PaperZPoint[];
  trades?: PaperTrade[];
  equity_curve?: PaperEquityPoint[];
  by_regime?: PaperByRegime[];
  stats?: Record<string, unknown>;
  error?: string;
}

export type PaperState = Record<string, PaperStructure>;

// ---- backtest (full-history intraday, model engine, flat 1-contract) ----
export interface BacktestSummary {
  n_trades: number;
  wins: number;
  win_rate: number;
  net_pnl_pts: number;
  net_pnl_usd: number;
  starting_equity: number;
  final_equity: number;
  max_drawdown_usd: number;
  first_bar?: string | null;
  last_bar?: string | null;
}

export interface BacktestStructure {
  key: string;
  label: string;
  n_trades: number;
  wins: number;
  win_rate: number;
  net_pnl_pts: number;
  net_pnl_usd: number;
  first_trade?: string | null;
  last_trade?: string | null;
}

export interface BacktestEquityPoint {
  ts: string | null;
  equity: number;
}

export interface BacktestTrade {
  key: string | null;
  label: string | null;
  direction: string | null;
  regime: string | null;
  confidence: string | null;
  entry_ts: string | null;
  entry_price: number | null;
  exit_ts: string | null;
  exit_price: number | null;
  exit_reason: string | null;
  target: number | null;
  stop: number | null;
  net_pnl_pts: number | null;
  net_pnl_usd: number | null;
  win: boolean;
  hold_bars: number | null;
}

// position still open at the end of the cached history (e.g. rolling c2-c3 finishing
// mid-trade) — a slimmer shape than the live PaperOpenPosition.
export interface BacktestOpenPosition {
  key: string;
  label: string;
  direction: string;
  entry_ts: string;
  entry_price: number;
  target: number;
  stop: number;
  regime: string | null;
}

export interface BacktestResult {
  available: boolean;
  generated_at?: string | null;
  sizing: string;
  contract_bbl: number;
  summary: BacktestSummary;
  structures: BacktestStructure[];
  equity_curve: BacktestEquityPoint[];
  trades: BacktestTrade[];        // ALL trades, newest first (frontend sizes + caps)
  trades_shown?: number;
  display_cap?: number;
  open_positions: BacktestOpenPosition[];
}

export interface PaperStructureListItem {
  key: string;
  label: string;
  instrument: string;
  structure: string;
  watch_only?: boolean;
}

export interface PaperStructuresResponse {
  structures: PaperStructureListItem[];
  thresholds: PaperThresholds;
}
