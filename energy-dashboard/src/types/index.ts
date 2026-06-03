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
