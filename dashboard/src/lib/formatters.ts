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
