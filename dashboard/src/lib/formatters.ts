export function fmt(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return '\u2014';
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fmtInt(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return '\u2014';
  return Number(n).toLocaleString('en-US');
}

export function fmtK(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return '\u2014';
  if (Math.abs(n) >= 1000) {
    return '$' + (n / 1000).toFixed(1) + 'K';
  }
  return fmt(n);
}

export function pct(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return '\u2014';
  return (n >= 0 ? '+' : '') + Number(n).toFixed(1) + '%';
}

export function pctPlain(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return '\u2014';
  return Number(n).toFixed(1) + '%';
}

export function ratio(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return '\u2014';
  return Number(n).toFixed(2) + 'x';
}

export function calcPct(a: number | null | undefined, b: number | null | undefined): number | null {
  if (a == null || b == null || !b) return null;
  return (a - b) / b * 100;
}

export function safe(n: number | null | undefined, fallback: number = 0): number {
  return (n == null || isNaN(n)) ? fallback : n;
}

export function badgeColor(val: number | null | undefined, positiveIsGood: boolean = true): 'success' | 'danger' | 'default' {
  if (val == null) return 'default';
  if (positiveIsGood) return val >= 0 ? 'success' : 'danger';
  return val <= 0 ? 'success' : 'danger';
}

export function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

export function linearProjection(dailyCY: { date: string; revenue: number }[]): number | null {
  if (!dailyCY || dailyCY.length < 2) return null;
  const n = dailyCY.length;
  const totalRev = dailyCY.reduce((s, d) => s + safe(d.revenue), 0);
  const avgDaily = totalRev / n;
  const firstDate = new Date(dailyCY[0].date);
  const dim = daysInMonth(firstDate.getFullYear(), firstDate.getMonth() + 1);
  return avgDaily * dim;
}

export interface RunRateResult {
  runRate: number;        // projected month-end total ($)
  trendPerDay: number;    // OLS slope — $ change per day (negative = declining)
  recentTrendPerDay: number; // slope of last 7 days only
  avgDaily: number;       // simple daily average so far
  daysElapsed: number;
  daysTotal: number;
  trendR2: number;        // 0–1, how well the trend line fits (signal quality)
}

function olsSlope(revs: number[]): { slope: number; intercept: number; r2: number } {
  const n = revs.length;
  const xMean = (n - 1) / 2;
  const yMean = revs.reduce((a, b) => a + b, 0) / n;
  const ssxx = revs.reduce((s, _, i) => s + (i - xMean) ** 2, 0);
  const ssxy = revs.reduce((s, y, i) => s + (i - xMean) * (y - yMean), 0);
  const slope = ssxx > 0 ? ssxy / ssxx : 0;
  const intercept = yMean - slope * xMean;
  const ssTot = revs.reduce((s, y) => s + (y - yMean) ** 2, 0);
  const ssRes = revs.reduce((s, y, i) => s + (y - (intercept + slope * i)) ** 2, 0);
  const r2 = ssTot > 0 ? Math.max(0, 1 - ssRes / ssTot) : 0;
  return { slope, intercept, r2 };
}

export function trendRunRate(dailyCY: { date: string; revenue: number }[]): RunRateResult | null {
  if (!dailyCY || dailyCY.length < 2) return null;

  const revs = dailyCY.map(d => safe(d.revenue));
  const n = revs.length;
  const actualToDate = revs.reduce((a, b) => a + b, 0);
  const avgDaily = actualToDate / n;

  const firstDate = new Date(dailyCY[0].date + 'T00:00:00');
  const dim = daysInMonth(firstDate.getFullYear(), firstDate.getMonth() + 1);
  const remainingDays = dim - n;

  if (remainingDays <= 0) {
    return { runRate: actualToDate, trendPerDay: 0, recentTrendPerDay: 0, avgDaily, daysElapsed: n, daysTotal: dim, trendR2: 0 };
  }

  // Full-period OLS regression
  const full = olsSlope(revs);

  // Recent 7-day OLS (captures acceleration or deceleration)
  const recentRevs = revs.slice(-Math.min(7, n));
  const recent = recentRevs.length >= 3 ? olsSlope(recentRevs) : full;
  // Translate recent regression to global day indices
  const recentStartIdx = n - recentRevs.length;
  const recentIntercept = recent.intercept - recent.slope * recentStartIdx;

  // Blend full-period and recent-period projections.
  // Weight recent more when it has strong signal and diverges from full trend.
  // This catches "month started strong, now decelerating" patterns.
  const recentWeight = n >= 7 ? Math.min(recent.r2, 0.6) : 0;
  const fullWeight = 1 - recentWeight;

  let fullProjected = 0;
  let recentProjected = 0;
  for (let d = n; d < dim; d++) {
    fullProjected += Math.max(0, full.intercept + full.slope * d);
    recentProjected += Math.max(0, recentIntercept + recent.slope * d);
  }

  // Final blend: trend vs simple average, weighted by full R² (trust trend only when it fits well)
  const trendBlended = fullWeight * fullProjected + recentWeight * recentProjected;
  const simpleProjected = avgDaily * remainingDays;
  const trendConfidence = n >= 5 ? Math.min(full.r2, 0.85) : 0;
  const projected = trendConfidence * trendBlended + (1 - trendConfidence) * simpleProjected;

  return {
    runRate: actualToDate + projected,
    trendPerDay: full.slope,
    recentTrendPerDay: recent.slope,
    avgDaily,
    daysElapsed: n,
    daysTotal: dim,
    trendR2: full.r2,
  };
}

export function cumulative(arr: number[]): number[] {
  let sum = 0;
  return arr.map(v => { sum += safe(v); return sum; });
}

export function shortDate(dateStr: string): string {
  const dt = new Date(dateStr + 'T00:00:00');
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function monthLabel(monthStr: string): string {
  const [y, m] = monthStr.split('-');
  const dt = new Date(Number(y), Number(m) - 1);
  return dt.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}
