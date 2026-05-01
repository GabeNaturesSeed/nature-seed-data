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
  runRate: number;            // projected month-end total ($)
  trendPerDay: number;        // OLS slope — $ change per day (negative = declining)
  recentTrendPerDay: number;  // slope of last 7 days only
  avgDaily: number;           // simple daily average so far
  daysElapsed: number;
  daysTotal: number;
  trendR2: number;            // 0–1, OLS fit quality
  lyScalingRatio: number | null; // CY-to-LY ratio observed so far (e.g. 1.12 = running 12% ahead of LY)
  modelWeights: { ly: number; ols: number; avg: number }; // share each component contributed to the projection
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

/**
 * trendRunRate — 3-component blended projection
 *
 * Component 1 — LY Seasonality Scaling (highest priority when available)
 *   Uses last-year daily revenue for the same calendar month, scaled by the
 *   CY/LY ratio observed so far. This captures day-of-month shape (e.g. end-
 *   of-month spikes, slow Sundays) that OLS cannot see. Weight grows with LY
 *   data coverage for remaining days and number of elapsed days.
 *
 * Component 2 — OLS Trend (blended full-period + recent-7-day regression)
 *   Captures intra-month acceleration/deceleration. Weighted by R² fit quality.
 *
 * Component 3 — Simple Daily Average (fallback / anchor)
 *   Pure mean × remaining days. Used when both LY data and OLS signal are weak.
 *
 * dailyLY dates must be the LY actual dates shifted +1 year so that
 * day-of-month aligns with dailyCY (this is how generate_data.py stores them).
 */
export function trendRunRate(
  dailyCY: { date: string; revenue: number }[],
  dailyLY?: { date: string; revenue: number }[],
): RunRateResult | null {
  if (!dailyCY || dailyCY.length < 2) return null;

  const revs = dailyCY.map(d => safe(d.revenue));
  const n = revs.length;
  const actualToDate = revs.reduce((a, b) => a + b, 0);
  const avgDaily = actualToDate / n;

  const firstDate = new Date(dailyCY[0].date + 'T00:00:00');
  const dim = daysInMonth(firstDate.getFullYear(), firstDate.getMonth() + 1);
  const remainingDays = dim - n;

  const zeroWeights = { ly: 0, ols: 0, avg: 1 };
  if (remainingDays <= 0) {
    return { runRate: actualToDate, trendPerDay: 0, recentTrendPerDay: 0, avgDaily, daysElapsed: n, daysTotal: dim, trendR2: 0, lyScalingRatio: null, modelWeights: zeroWeights };
  }

  // ── Component 2: OLS Trend ─────────────────────────────────────────────────
  const full = olsSlope(revs);
  const recentRevs = revs.slice(-Math.min(7, n));
  const recent = recentRevs.length >= 3 ? olsSlope(recentRevs) : full;
  const recentStartIdx = n - recentRevs.length;
  const recentIntercept = recent.intercept - recent.slope * recentStartIdx;
  const recentBlendWeight = n >= 7 ? Math.min(recent.r2, 0.6) : 0;

  let fullOlsProjected = 0;
  let recentOlsProjected = 0;
  for (let d = n; d < dim; d++) {
    fullOlsProjected  += Math.max(0, full.intercept + full.slope * d);
    recentOlsProjected += Math.max(0, recentIntercept + recent.slope * d);
  }
  const olsProjected = (1 - recentBlendWeight) * fullOlsProjected + recentBlendWeight * recentOlsProjected;

  // ── Component 1: LY Seasonality Scaling ───────────────────────────────────
  // Build day-of-month → LY revenue map.
  // dailyLY dates are shifted +365 days by the backend so day-of-month aligns.
  const lyByDay: Record<number, number> = {};
  if (dailyLY?.length) {
    for (const d of dailyLY) {
      const day = new Date(d.date + 'T00:00:00').getDate();
      lyByDay[day] = safe(d.revenue);
    }
  }

  // CY/LY ratio from elapsed days (only where both have data)
  let lyToDateMatched = 0;
  let cyToDateMatched = 0;
  for (let i = 0; i < n; i++) {
    const day = new Date(dailyCY[i].date + 'T00:00:00').getDate();
    if (lyByDay[day] != null) {
      lyToDateMatched += lyByDay[day];
      cyToDateMatched += revs[i];
    }
  }
  const lyScalingRatio = lyToDateMatched > 0 ? cyToDateMatched / lyToDateMatched : null;

  // Project remaining days using LY pattern × CY/LY ratio
  let lyProjected = 0;
  let lyDaysHit = 0;
  for (let d = n; d < dim; d++) {
    const day = d + 1; // day-of-month is 1-indexed
    if (lyByDay[day] != null && lyScalingRatio != null) {
      lyProjected += lyByDay[day] * lyScalingRatio;
      lyDaysHit++;
    } else {
      lyProjected += avgDaily; // no LY data for this day — fall back to average
    }
  }

  // LY coverage: fraction of remaining days that have LY data
  const lyCoverage = remainingDays > 0 ? lyDaysHit / remainingDays : 0;

  // ── Weight the three components ───────────────────────────────────────────
  // LY weight scales with: coverage of remaining days × elapsed days (need ≥3 to trust ratio)
  const lyDataQuality = n >= 3 ? lyCoverage : 0;
  const lyWeight = Math.min(lyDataQuality * 0.65, 0.65);

  // OLS weight: trust the trend only when it fits well and month is mature enough
  const olsConfidence = n >= 5 ? Math.min(full.r2, 0.85) : 0;

  // Non-LY portion split between OLS and simple average by OLS confidence
  const nonLyWeight = 1 - lyWeight;
  const olsWeight   = nonLyWeight * olsConfidence;
  const avgWeight   = nonLyWeight * (1 - olsConfidence);

  const simpleProjected = avgDaily * remainingDays;
  const projected = lyWeight * lyProjected + olsWeight * olsProjected + avgWeight * simpleProjected;

  return {
    runRate: actualToDate + projected,
    trendPerDay: full.slope,
    recentTrendPerDay: recent.slope,
    avgDaily,
    daysElapsed: n,
    daysTotal: dim,
    trendR2: full.r2,
    lyScalingRatio,
    modelWeights: { ly: lyWeight, ols: olsWeight, avg: avgWeight },
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
