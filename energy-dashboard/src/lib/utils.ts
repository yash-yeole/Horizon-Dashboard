import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(value: number, decimals = 2): string {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatChange(value: number, decimals = 2): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}`;
}

export function formatPercent(value: number, decimals = 2): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatVolume(value: string | number): string {
  if (typeof value === 'number') {
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
    return value.toString();
  }
  return value;
}

export function formatCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString('en-US');
}

export function generateSparkline(base: number, points = 20, volatility = 0.02): number[] {
  const result: number[] = [base];
  for (let i = 1; i < points; i++) {
    const prev = result[i - 1];
    const change = prev * volatility * (Math.random() - 0.48);
    result.push(+(prev + change).toFixed(2));
  }
  return result;
}

export function generateTimeSeries(
  base: number,
  points: number,
  volatility = 0.01,
  labelFn?: (i: number) => string
): Array<{ time: string; value: number }> {
  const data: Array<{ time: string; value: number }> = [];
  let current = base;
  const now = new Date();
  for (let i = points - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const change = current * volatility * (Math.random() - 0.48);
    current = +(current + change).toFixed(2);
    data.push({
      time: labelFn ? labelFn(i) : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: current,
    });
  }
  return data;
}

export function getChangeColor(value: number): string {
  if (value > 0) return 'text-green-400';
  if (value < 0) return 'text-red-400';
  return 'text-slate-400';
}

export function getChangeBg(value: number): string {
  if (value > 0) return 'bg-green-500/10 text-green-400';
  if (value < 0) return 'bg-red-500/10 text-red-400';
  return 'bg-slate-500/10 text-slate-400';
}

export function utcTime(): string {
  return new Date().toUTCString().slice(17, 22) + ' UTC';
}
