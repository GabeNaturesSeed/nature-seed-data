'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { fmt, fmtK, ratio } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import { Skeleton } from '@heroui/react';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer,
} from 'recharts';

interface BudgetMonth {
  month: string;
  status: 'mtd' | 'future';
  days_with_data: number;
  budget_ad: number;
  budget_rev: number;
  budget_ebitda: number;
  ad_actual: number | null;
  rev_actual: number | null;
  ebitda_actual: number | null;
  roas_actual: number | null;
  mer_actual: number | null;
}

interface LivingBudgetData {
  generated_at: string;
  as_of: string;
  annual_budget: number;
  spent_jan_apr: number;
  remaining: number;
  annual_ebitda_target: number;
  q1_apr_ebitda: number;
  current_month: string;
  current_roas: number | null;
  current_mer: number | null;
  months: BudgetMonth[];
}

function monthLabel(m: string): string {
  const [y, mo] = m.split('-');
  return new Date(Number(y), Number(mo) - 1, 1).toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
}

function statusBadge(s: BudgetMonth['status'], ebitdaGap: number | null) {
  if (s === 'future') return <span className="px-2 py-0.5 rounded-full text-[10px] bg-brand-neutral/10 text-brand-neutral/50">Upcoming</span>;
  if (ebitdaGap == null) return <span className="px-2 py-0.5 rounded-full text-[10px] bg-ns-yellow/20 text-ns-yellow">MTD</span>;
  if (ebitdaGap >= -500) return <span className="px-2 py-0.5 rounded-full text-[10px] bg-brand-primary/15 text-brand-primary">On Track</span>;
  if (ebitdaGap >= -5000) return <span className="px-2 py-0.5 rounded-full text-[10px] bg-ns-yellow/20 text-ns-yellow">Watch</span>;
  return <span className="px-2 py-0.5 rounded-full text-[10px] bg-ns-red/15 text-ns-red">Behind</span>;
}

function GaugeBar({ value, target, label, note }: { value: number | null; target: number; label: string; note: string }) {
  const pct = value != null ? Math.min((value / (target * 1.5)) * 100, 100) : 0;
  const targetPct = (target / (target * 1.5)) * 100;
  const color = value == null ? '#bfc9c1' : value >= target ? '#3a7a45' : value >= target * 0.8 ? '#c96a2e' : '#c0392b';
  return (
    <div className="bg-surface-lowest rounded-xl shadow-ambient p-5 flex-1">
      <div className="text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold mb-3">{label}</div>
      <div className="text-3xl font-display font-bold mb-1" style={{ color }}>
        {value != null ? ratio(value) : '—'}
      </div>
      <div className="text-xs text-brand-neutral/50 mb-3">Target: {ratio(target)}</div>
      <div className="relative h-2.5 bg-brand-neutral/10 rounded-full overflow-hidden">
        <div className="absolute inset-y-0 left-0 rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
        <div className="absolute inset-y-0 w-0.5 bg-brand-neutral/40" style={{ left: `${targetPct}%` }} />
      </div>
      <div className="text-[11px] text-brand-neutral/40 mt-2">{note}</div>
    </div>
  );
}

export default function LivingBudgetPage() {
  const { data, loading } = useJsonData<LivingBudgetData>('living-budget');

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64 rounded-xl" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
        <Skeleton className="h-72 rounded-xl" />
      </div>
    );
  }

  if (!data) return <p className="text-brand-neutral/50">Living budget data unavailable.</p>;

  const spentPct = data.annual_budget ? (data.spent_jan_apr / data.annual_budget) * 100 : 0;
  const remainingPct = 100 - spentPct;

  // Chart data — EBITDA budget vs actual with cumulative lines
  let cumBudget = 0;
  let cumActual = 0;
  const chartData = data.months.map(m => {
    cumBudget += m.budget_ebitda;
    const actual = m.ebitda_actual ?? null;
    if (actual != null) cumActual += actual;
    return {
      name: monthLabel(m.month),
      budgetEbitda: m.budget_ebitda,
      actualEbitda: actual,
      cumBudget,
      cumActual: actual != null ? cumActual : null,
    };
  });

  // Budget remaining tracker
  const totalFutureBudget = data.months.reduce((s, m) => s + m.budget_ad, 0);
  const spentFuture = data.months.reduce((s, m) => s + (m.ad_actual ?? 0), 0);
  const remainingFuture = totalFutureBudget - spentFuture;
  const daysWithData = data.months.reduce((s, m) => s + m.days_with_data, 0);
  const dailyRunRate = daysWithData > 0 ? spentFuture / daysWithData : null;
  const daysUntilExhausted = dailyRunRate && remainingFuture > 0 ? Math.round(remainingFuture / dailyRunRate) : null;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <div>
          <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">Living Budget</h1>
          <p className="text-[11px] md:text-xs text-brand-neutral/60 mt-1">
            Ad spend · Revenue · EBITDA vs budget · May–Dec remaining
          </p>
        </div>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">As of {data.as_of}</span>
      </div>

      {/* Annual snapshot KPIs */}
      <KpiGrid columns={4}>
        <KpiCard label="Annual Ad Budget" value={fmt(data.annual_budget)} />
        <KpiCard
          label="Spent Jan–Apr"
          value={fmt(data.spent_jan_apr)}
          badges={[{ label: `${spentPct.toFixed(0)}% of annual`, color: spentPct > 70 ? 'danger' : 'default' }]}
        />
        <KpiCard label="Remaining May–Dec" value={fmt(data.remaining)} />
        <KpiCard
          label="EBITDA Jan–Apr Actual"
          value={fmt(data.q1_apr_ebitda)}
          badges={[{ label: `Target ${fmt(data.annual_ebitda_target)}`, color: 'default' }]}
        />
      </KpiGrid>

      {/* Progress bar */}
      <div className="bg-surface-lowest rounded-xl shadow-ambient p-5 mb-6">
        <div className="flex items-center justify-between text-xs text-brand-neutral/60 mb-2">
          <span>Budget consumed Jan–Apr</span>
          <span>{spentPct.toFixed(1)}% of {fmt(data.annual_budget)}</span>
        </div>
        <div className="h-3 bg-brand-neutral/10 rounded-full overflow-hidden flex">
          <div className="h-full bg-brand-primary rounded-l-full transition-all" style={{ width: `${spentPct}%` }} />
          <div className="h-full bg-brand-primary/20 rounded-r-full transition-all" style={{ width: `${remainingPct}%` }} />
        </div>
        <div className="flex justify-between text-[10px] text-brand-neutral/40 mt-1.5">
          <span>Spent {fmt(data.spent_jan_apr)}</span>
          <span>Remaining {fmt(data.remaining)}</span>
        </div>
      </div>

      {/* Monthly table */}
      <div className="bg-surface-lowest rounded-xl shadow-ambient overflow-x-auto mb-6">
        <table className="w-full text-sm border-collapse min-w-[800px]">
          <thead>
            <tr className="bg-surface-low">
              {['Month', 'Budget Ad', 'Actual Ad', 'Budget Rev', 'Actual Rev', 'Budget EBITDA', 'Actual EBITDA', 'EBITDA Gap', 'ROAS', 'MER', 'Status'].map(h => (
                <th key={h} className="text-right first:text-left px-4 py-3 text-[11px] uppercase tracking-wider text-brand-neutral/50 font-semibold">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.months.map(m => {
              const ebitdaGap = m.ebitda_actual != null ? m.ebitda_actual - m.budget_ebitda : null;
              const revGap = m.rev_actual != null ? m.rev_actual - m.budget_rev : null;
              return (
                <tr key={m.month} className="border-t border-brand-neutral/5 hover:bg-surface-low transition-colors">
                  <td className="px-4 py-2.5 font-semibold text-brand-neutral">{monthLabel(m.month)}</td>
                  <td className="px-4 py-2.5 text-right text-brand-neutral/70">{fmtK(m.budget_ad)}</td>
                  <td className="px-4 py-2.5 text-right">{m.ad_actual != null ? fmtK(m.ad_actual) : <span className="text-brand-neutral/30">—</span>}</td>
                  <td className="px-4 py-2.5 text-right text-brand-neutral/70">{fmtK(m.budget_rev)}</td>
                  <td className="px-4 py-2.5 text-right">{m.rev_actual != null ? fmtK(m.rev_actual) : <span className="text-brand-neutral/30">—</span>}</td>
                  <td className="px-4 py-2.5 text-right text-brand-neutral/70">{fmtK(m.budget_ebitda)}</td>
                  <td className="px-4 py-2.5 text-right font-semibold">{m.ebitda_actual != null ? fmtK(m.ebitda_actual) : <span className="text-brand-neutral/30">—</span>}</td>
                  <td className={`px-4 py-2.5 text-right font-semibold ${ebitdaGap != null ? (ebitdaGap >= 0 ? 'text-brand-primary' : 'text-ns-red') : ''}`}>
                    {ebitdaGap != null ? (ebitdaGap >= 0 ? '+' : '') + fmtK(ebitdaGap) : <span className="text-brand-neutral/30">—</span>}
                  </td>
                  <td className="px-4 py-2.5 text-right">{m.roas_actual != null ? ratio(m.roas_actual) : <span className="text-brand-neutral/30">—</span>}</td>
                  <td className="px-4 py-2.5 text-right">{m.mer_actual != null ? ratio(m.mer_actual) : <span className="text-brand-neutral/30">—</span>}</td>
                  <td className="px-4 py-2.5 text-right">{statusBadge(m.status, ebitdaGap)}</td>
                </tr>
              );
            })}
            {/* Totals row */}
            <tr className="border-t-2 border-brand-neutral/15 bg-surface-low font-semibold">
              <td className="px-4 py-2.5">Totals</td>
              <td className="px-4 py-2.5 text-right">{fmtK(data.months.reduce((s, m) => s + m.budget_ad, 0))}</td>
              <td className="px-4 py-2.5 text-right">{fmtK(data.months.reduce((s, m) => s + (m.ad_actual ?? 0), 0))}</td>
              <td className="px-4 py-2.5 text-right">{fmtK(data.months.reduce((s, m) => s + m.budget_rev, 0))}</td>
              <td className="px-4 py-2.5 text-right">{fmtK(data.months.reduce((s, m) => s + (m.rev_actual ?? 0), 0))}</td>
              <td className="px-4 py-2.5 text-right">{fmtK(data.months.reduce((s, m) => s + m.budget_ebitda, 0))}</td>
              <td className="px-4 py-2.5 text-right">{fmtK(data.months.reduce((s, m) => s + (m.ebitda_actual ?? 0), 0))}</td>
              <td className="px-4 py-2.5 text-right" />
              <td className="px-4 py-2.5 text-right" />
              <td className="px-4 py-2.5 text-right" />
              <td className="px-4 py-2.5 text-right" />
            </tr>
          </tbody>
        </table>
      </div>

      {/* EBITDA chart */}
      <div className="bg-surface-lowest rounded-xl shadow-ambient p-5 md:p-6 mb-6">
        <h2 className="text-sm font-semibold text-brand-neutral mb-4">EBITDA — Budget vs Actual (May–Dec)</h2>
        <div className="h-72">
          <ResponsiveContainer>
            <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#2c3e2b' }} />
              <YAxis yAxisId="monthly" tick={{ fontSize: 10, fill: '#2c3e2b' }} tickFormatter={v => '$' + (v / 1000).toFixed(0) + 'K'} />
              <YAxis yAxisId="cum" orientation="right" tick={{ fontSize: 10, fill: '#2c3e2b' }} tickFormatter={v => '$' + (v / 1000).toFixed(0) + 'K'} />
              <ReferenceLine yAxisId="monthly" y={0} stroke="#999" strokeDasharray="2 2" />
              <Tooltip formatter={(v, name) => [fmtK(Number(v)), name]} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar yAxisId="monthly" dataKey="budgetEbitda" name="Budget EBITDA" fill="rgba(90,143,180,0.35)" radius={[3, 3, 0, 0]} />
              <Bar yAxisId="monthly" dataKey="actualEbitda" name="Actual EBITDA" fill="#3a7a45" radius={[3, 3, 0, 0]} />
              <Line yAxisId="cum" type="monotone" dataKey="cumBudget" name="Cum. Budget" stroke="#5a8fb4" strokeWidth={1.5} strokeDasharray="4 3" dot={false} />
              <Line yAxisId="cum" type="monotone" dataKey="cumActual" name="Cum. Actual" stroke="#2d6a4f" strokeWidth={2} dot={{ r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Efficiency gauges + budget tracker */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <GaugeBar
          value={data.current_roas}
          target={3.0}
          label="Current ROAS"
          note="Target 3.0x — revenue generated per $1 of ad spend"
        />
        <GaugeBar
          value={data.current_mer}
          target={5.1}
          label="Current MER"
          note="Target 5.1x — total revenue ÷ total ad spend (blended efficiency)"
        />
        <div className="bg-surface-lowest rounded-xl shadow-ambient p-5 flex-1">
          <div className="text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold mb-3">Budget Remaining Tracker</div>
          <div className="text-3xl font-display font-bold text-brand-primary mb-1">{fmtK(remainingFuture)}</div>
          <div className="text-xs text-brand-neutral/50 mb-3">of {fmtK(totalFutureBudget)} May–Dec budget</div>
          <div className="h-2.5 bg-brand-neutral/10 rounded-full overflow-hidden mb-2">
            <div
              className="h-full bg-brand-primary rounded-full"
              style={{ width: `${totalFutureBudget ? Math.min((spentFuture / totalFutureBudget) * 100, 100) : 0}%` }}
            />
          </div>
          {dailyRunRate != null && (
            <div className="text-[11px] text-brand-neutral/50">
              {fmtK(dailyRunRate)}/day pace ·{' '}
              {daysUntilExhausted != null
                ? `~${daysUntilExhausted} days remaining`
                : 'tracking...'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
