import type { Commodity } from '@/types';
import { generateSparkline } from '@/lib/utils';

export const HERO_METRICS: Commodity[] = [
  {
    id: 'brent', name: 'Brent Crude', symbol: 'BRN', price: 82.47, change: 1.23,
    changePct: 1.51, high: 83.10, low: 80.95, volume: '245.3K', unit: 'bbl',
    currency: 'USD', category: 'crude', sparkline: generateSparkline(82, 24, 0.012),
  },
  {
    id: 'wti', name: 'WTI Crude', symbol: 'CLc1', price: 78.32, change: 0.98,
    changePct: 1.27, high: 78.95, low: 76.80, volume: '312.1K', unit: 'bbl',
    currency: 'USD', category: 'crude', sparkline: generateSparkline(78, 24, 0.012),
  },
  {
    id: 'rbob', name: 'RBOB Gasoline', symbol: 'RB', price: 2.41, change: 0.03,
    changePct: 1.26, high: 2.44, low: 2.37, volume: '98.0K', unit: 'gal',
    currency: 'USD', category: 'products', sparkline: generateSparkline(2.41, 24, 0.015),
  },
  {
    id: 'heatoil', name: 'Heating Oil', symbol: 'HO', price: 2.58, change: -0.02,
    changePct: -0.77, high: 2.61, low: 2.56, volume: '76.0K', unit: 'gal',
    currency: 'USD', category: 'products', sparkline: generateSparkline(2.58, 24, 0.015),
  },
  {
    id: 'gasoil', name: 'Gas Oil', symbol: 'GO', price: 742.5, change: 8.25,
    changePct: 1.12, high: 748, low: 730, volume: '64.0K', unit: 'mt',
    currency: 'USD', category: 'products', sparkline: generateSparkline(742.5, 24, 0.012),
  },
  {
    id: 'vix', name: 'VIX', symbol: 'VIX', price: 14.28, change: -0.62,
    changePct: -4.16, high: 15.10, low: 14.05, volume: '—', unit: 'idx',
    currency: '', category: 'macro', sparkline: generateSparkline(14.28, 24, 0.04),
  },
  {
    id: 'dxy', name: 'DXY', symbol: 'DXY', price: 104.32, change: 0.18,
    changePct: 0.17, high: 104.50, low: 104.05, volume: '—', unit: 'idx',
    currency: '', category: 'macro', sparkline: generateSparkline(104.32, 24, 0.004),
  },
];

export const CRUDE_GRADES: Commodity[] = [
  { id: 'brent', name: 'Brent', symbol: 'BRN', price: 82.47, change: 1.23, changePct: 1.51, high: 83.1, low: 80.95, volume: '245K', unit: 'bbl', currency: 'USD', category: 'crude', sparkline: generateSparkline(82, 20) },
  { id: 'wti', name: 'WTI', symbol: 'CLc1', price: 78.32, change: 0.98, changePct: 1.27, high: 78.95, low: 76.8, volume: '312K', unit: 'bbl', currency: 'USD', category: 'crude', sparkline: generateSparkline(78, 20) },
  { id: 'dubai', name: 'Dubai', symbol: 'DUB', price: 81.05, change: 0.76, changePct: 0.95, high: 81.5, low: 80.1, volume: '88K', unit: 'bbl', currency: 'USD', category: 'crude', sparkline: generateSparkline(81, 20) },
  { id: 'urals', name: 'Urals', symbol: 'URL', price: 68.42, change: -0.34, changePct: -0.49, high: 69.2, low: 68.1, volume: '42K', unit: 'bbl', currency: 'USD', category: 'crude', sparkline: generateSparkline(68, 20) },
  { id: 'wcs', name: 'WCS', symbol: 'WCS', price: 64.18, change: 0.52, changePct: 0.82, high: 64.8, low: 63.5, volume: '31K', unit: 'bbl', currency: 'USD', category: 'crude', sparkline: generateSparkline(64, 20) },
  { id: 'bonny', name: 'Bonny Light', symbol: 'BNL', price: 83.91, change: 1.42, changePct: 1.72, high: 84.2, low: 82.4, volume: '18K', unit: 'bbl', currency: 'USD', category: 'crude', sparkline: generateSparkline(83, 20) },
];

export const PRODUCTS: Commodity[] = [
  { id: 'rbob', name: 'RBOB Gasoline', symbol: 'RB', price: 2.41, change: 0.03, changePct: 1.26, high: 2.44, low: 2.37, volume: '98K', unit: 'gal', currency: 'USD', category: 'products', sparkline: generateSparkline(2.41, 20) },
  { id: 'heatoil', name: 'Heating Oil', symbol: 'HO', price: 2.58, change: -0.02, changePct: -0.77, high: 2.61, low: 2.56, volume: '76K', unit: 'gal', currency: 'USD', category: 'products', sparkline: generateSparkline(2.58, 20) },
  { id: 'gasoil', name: 'Gasoil', symbol: 'GO', price: 742.5, change: 8.25, changePct: 1.12, high: 748, low: 730, volume: '64K', unit: 'mt', currency: 'USD', category: 'products', sparkline: generateSparkline(742, 20) },
  { id: 'jet', name: 'Jet Fuel', symbol: 'JET', price: 2.71, change: 0.04, changePct: 1.5, high: 2.73, low: 2.66, volume: '22K', unit: 'gal', currency: 'USD', category: 'products', sparkline: generateSparkline(2.71, 20) },
  { id: 'naphtha', name: 'Naphtha', symbol: 'NAP', price: 685.0, change: -3.5, changePct: -0.51, high: 690, low: 682, volume: '14K', unit: 'mt', currency: 'USD', category: 'products', sparkline: generateSparkline(685, 20) },
  { id: 'fueloil', name: 'Fuel Oil 3.5%', symbol: 'FO', price: 478.2, change: 2.1, changePct: 0.44, high: 480, low: 474, volume: '19K', unit: 'mt', currency: 'USD', category: 'products', sparkline: generateSparkline(478, 20) },
];

export interface MarketMover {
  name: string;
  symbol: string;
  changePct: number;
  price: number;
}

export const TOP_GAINERS: MarketMover[] = [
  { name: 'Bonny Light', symbol: 'BNL', changePct: 1.72, price: 83.91 },
  { name: 'Brent', symbol: 'BRN', changePct: 1.51, price: 82.47 },
  { name: 'Jet Fuel', symbol: 'JET', changePct: 1.50, price: 2.71 },
  { name: 'RBOB Gasoline', symbol: 'RB', changePct: 1.26, price: 2.41 },
  { name: 'Gas Oil', symbol: 'GO', changePct: 1.12, price: 742.5 },
];

export const TOP_LOSERS: MarketMover[] = [
  { name: 'VIX', symbol: 'VIX', changePct: -4.16, price: 14.28 },
  { name: 'Heating Oil', symbol: 'HO', changePct: -0.77, price: 2.58 },
  { name: 'Naphtha', symbol: 'NAP', changePct: -0.51, price: 685.0 },
  { name: 'Urals', symbol: 'URL', changePct: -0.49, price: 68.42 },
  { name: 'Fuel Oil 3.5%', symbol: 'FO', changePct: -0.30, price: 478.2 },
];
