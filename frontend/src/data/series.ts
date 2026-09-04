import { generateTimeSeries } from '@/lib/utils';
import type { SpreadData, CorrelationEntry } from '@/types';

export const brentSeries = generateTimeSeries(82, 90, 0.012);
export const wtiSeries = generateTimeSeries(78, 90, 0.012);
export const rbobSeries = generateTimeSeries(2.41, 90, 0.015);
export const heatoilSeries = generateTimeSeries(2.58, 90, 0.014);

// Multi-commodity comparison (normalized to 100 base)
export const comparisonSeries = (() => {
  const days = 60;
  const data: Array<Record<string, number | string>> = [];
  let brent = 100, wti = 100, rbob = 100, heatoil = 100;
  const now = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    brent += brent * 0.01 * (Math.random() - 0.48);
    wti += wti * 0.011 * (Math.random() - 0.48);
    rbob += rbob * 0.014 * (Math.random() - 0.48);
    heatoil += heatoil * 0.013 * (Math.random() - 0.48);
    data.push({
      time: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      Brent: +brent.toFixed(2),
      WTI: +wti.toFixed(2),
      RBOB: +rbob.toFixed(2),
      'Heating Oil': +heatoil.toFixed(2),
    });
  }
  return data;
})();

// Volume bars
export const volumeSeries = (() => {
  const data = [];
  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    data.push({
      time: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: +(150 + Math.random() * 200).toFixed(0),
      price: +(80 + Math.random() * 5).toFixed(2),
    });
  }
  return data;
})();

export const SPREADS: SpreadData[] = [
  { name: 'Brent-WTI', value: 4.15, change: 0.25, history: Array.from({ length: 20 }, () => +(4 + Math.random()).toFixed(2)) },
  { name: 'Crack 3:2:1', value: 22.84, change: -0.43, history: Array.from({ length: 20 }, () => +(22 + Math.random() * 2).toFixed(2)) },
  { name: 'RBOB-Brent', value: 12.18, change: 0.34, history: Array.from({ length: 20 }, () => +(12 + Math.random() * 1.5).toFixed(2)) },
  { name: 'Gasoil-Brent', value: 18.42, change: 0.61, history: Array.from({ length: 20 }, () => +(18 + Math.random() * 1.5).toFixed(2)) },
  { name: 'WTI-Dubai', value: -2.73, change: -0.12, history: Array.from({ length: 20 }, () => +(-3 + Math.random()).toFixed(2)) },
  { name: 'Gas Oil-Heat', value: 1.85, change: 0.05, history: Array.from({ length: 20 }, () => +(1.5 + Math.random()).toFixed(2)) },
];

// Correlation matrix
const ASSETS = ['Brent', 'WTI', 'RBOB', 'HO', 'Gasoil', 'DXY', 'VIX', 'S&P'];
export const correlationMatrix: CorrelationEntry[] = ASSETS.map((asset, i) => {
  const values: Record<string, number> = {};
  ASSETS.forEach((other, j) => {
    if (i === j) values[other] = 1;
    else {
      const seed = Math.sin(i * 12.9898 + j * 78.233) * 43758.5453;
      values[other] = +((seed - Math.floor(seed)) * 2 - 1).toFixed(2);
    }
  });
  return { asset, values };
});
export const CORRELATION_ASSETS = ASSETS;
