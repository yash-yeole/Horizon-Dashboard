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

export interface CurvePoint {
  month: string;
  price: number;
  previousPrice: number;
}

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
