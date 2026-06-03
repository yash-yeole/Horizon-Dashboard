import type { CommodityCategory } from '@/types';

/**
 * Yahoo Finance symbol mapping for the HORIZON terminal.
 * `id` matches the ids used in the static dummy data so live values
 * can be merged into existing cards. `yahoo` is the Yahoo ticker.
 */
export interface SymbolDef {
  id: string;
  yahoo: string;
  name: string;
  unit: string;
  currency: string;
  category: CommodityCategory;
}

export const YAHOO_SYMBOLS: SymbolDef[] = [
  { id: 'brent', yahoo: 'BZ=F', name: 'Brent Crude', unit: 'bbl', currency: 'USD', category: 'crude' },
  { id: 'wti', yahoo: 'CL=F', name: 'WTI Crude', unit: 'bbl', currency: 'USD', category: 'crude' },
  { id: 'vix', yahoo: '^VIX', name: 'VIX', unit: 'idx', currency: '', category: 'macro' },
  { id: 'dxy', yahoo: 'DX-Y.NYB', name: 'DXY', unit: 'idx', currency: '', category: 'macro' },
];

// Additional macro / cross-asset tickers (used on the Macro page).
export const YAHOO_MACRO: SymbolDef[] = [
  { id: 'sp500', yahoo: '^GSPC', name: 'S&P 500', unit: 'idx', currency: '', category: 'macro' },
  { id: 'ust10y', yahoo: '^TNX', name: 'US 10Y Yield', unit: '%', currency: '', category: 'macro' },
  { id: 'gold', yahoo: 'GC=F', name: 'Gold', unit: 'oz', currency: 'USD', category: 'macro' },
  { id: 'copper', yahoo: 'HG=F', name: 'Copper', unit: 'lb', currency: 'USD', category: 'macro' },
];

// Refined products available on Yahoo.
export const YAHOO_PRODUCTS: SymbolDef[] = [
  { id: 'rbob', yahoo: 'RB=F', name: 'RBOB Gasoline', unit: 'gal', currency: 'USD', category: 'products' },
  { id: 'heatoil', yahoo: 'HO=F', name: 'Heating Oil', unit: 'gal', currency: 'USD', category: 'products' },
];

export const ALL_YAHOO = [...YAHOO_SYMBOLS, ...YAHOO_MACRO, ...YAHOO_PRODUCTS];

export const symbolById = (id: string): SymbolDef | undefined =>
  ALL_YAHOO.find((s) => s.id === id);
