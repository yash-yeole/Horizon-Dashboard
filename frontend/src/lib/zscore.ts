// Robust z-score anomaly stats for the statistical alert layer.
//
// We use the MEDIAN + MAD (median absolute deviation) instead of mean + std so a
// single shock in the history can't inflate sigma and mask the next anomaly
// ("masking"). With the 1.4826 scaling, robust sigma ≈ classic std on clean data,
// so we lose nothing when the series is well-behaved. Our z = (x − median) /
// (1.4826·MAD) is exactly the NIST/Iglewicz–Hoaglin "modified z-score".

export const ZTHRESH = { watch: 1.5, elevated: 2.0, high: 3.0 } as const;
export const TIER_NAMES = ['none', 'watch', 'elevated', 'high'] as const;
export type TierName = (typeof TIER_NAMES)[number];

/** Tier level from |z|: 0 none, 1 watch, 2 elevated, 3 high. */
export function zTierLevel(absZ: number): number {
  if (absZ >= ZTHRESH.high) return 3;
  if (absZ >= ZTHRESH.elevated) return 2;
  if (absZ >= ZTHRESH.watch) return 1;
  return 0;
}

function median(xs: number[]): number {
  const a = [...xs].sort((p, q) => p - q);
  const n = a.length;
  if (!n) return NaN;
  return n % 2 ? a[(n - 1) / 2] : (a[n / 2 - 1] + a[n / 2]) / 2;
}

function classicStd(xs: number[], mean: number): number {
  if (xs.length < 2) return 0;
  const v = xs.reduce((s, x) => s + (x - mean) ** 2, 0) / (xs.length - 1);
  return Math.sqrt(v);
}

export interface ZStat {
  value: number;   // current observation (last point)
  center: number;  // robust center (median)
  sigma: number;   // robust sigma (1.4826·MAD, std fallback)
  z: number;       // (value − center) / sigma
  n: number;       // sample size used
}

/**
 * Robust z of the latest point vs a trailing baseline.
 * `window` caps how many trailing points form the baseline (default: all).
 * Returns null when there isn't enough history (< 8 points) to be meaningful.
 */
export function robustZ(series: number[], window?: number): ZStat | null {
  const clean = series.filter((x) => Number.isFinite(x));
  if (clean.length < 8) return null;
  const w = window ? clean.slice(-window) : clean;
  const n = w.length;
  const value = w[n - 1];
  const center = median(w);
  const mad = median(w.map((x) => Math.abs(x - center)));
  let sigma = 1.4826 * mad;
  if (!(sigma > 0)) {
    // Degenerate MAD (e.g. many identical values) → fall back to classic std.
    const mean = w.reduce((s, x) => s + x, 0) / n;
    sigma = classicStd(w, mean);
  }
  if (!(sigma > 0)) return { value, center, sigma: 0, z: 0, n };
  return { value, center, sigma, z: (value - center) / sigma, n };
}

/**
 * Apply hysteresis so a value wobbling around a threshold doesn't re-fire.
 * Returns the effective tier given the previous tier and a re-arm buffer:
 * once in a tier, we only drop out when |z| falls below (entry − buffer).
 */
export function hysteresisTier(absZ: number, prevTier: number, buffer = 0.3): number {
  const raw = zTierLevel(absZ);
  if (raw >= prevTier) return raw;
  // raw < prevTier: only step down if we've cleared the lower band of prevTier.
  const entry = [0, ZTHRESH.watch, ZTHRESH.elevated, ZTHRESH.high][prevTier];
  return absZ >= entry - buffer ? prevTier : raw;
}
