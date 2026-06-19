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
