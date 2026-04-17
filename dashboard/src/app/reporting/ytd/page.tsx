'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { ReportingData, BudgetData } from '@/lib/types';
import { fmt, fmtInt, pct, ratio, calcPct, badgeColor, monthLabel, cumulative, safe, fmtK } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import ChartCard from '@/components/charts/ChartCard';
import { sources } from '@/lib/sources';
import { Skeleton } from '@heroui/react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';

const dollarFormatter = (v: number) => '$' + (v / 1000).toFixed(0) + 'K';

export default function YtdPage() {
  const { data: reporting, loading: loadingR } = useJsonData<ReportingData>('reporting');
  const { data: budget, loading: loadingB } = useJsonData<BudgetData>('budget');

  if (loadingR || loadingB) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (!reporting) return <p className="text-brand-neutral/50">Reporting data unavailable</p>;

  const { ytd } = reporting;
  const totCY = ytd.totals_cy;
  const totLY = ytd.totals_ly;
  const totBud = ytd.totals_budget;

  const revLyPct = calcPct(totCY.revenue, totLY.revenue);
  const revBudPct = calcPct(totCY.revenue, totBud.revenue);
  const adLyPct = calcPct(totCY.ad_spend, totLY.ad_spend);

  // Build cumulative YTD chart
  const months = ytd.months;
  const cyRevs = months.map(m => safe(m.revenue));
  const lyRevs = months.map(m => safe(m.ly_revenue));
  const budRevs = months.map(m => safe(m.budget_revenue));
  const cyCum = cumulative(cyRevs);
  const lyCum = cumulative(lyRevs);
  const budCum = cumulative(budRevs);

  // Add future budget months for projection
  const budgetMonths = budget ? Object.keys(budget.monthly).sort() : [];
  const existingMonths = new Set(months.map(m => m.month));
  const futureMonthLabels: string[] = [];
  const futureBudCum: (number | null)[] = [];
  let runningBudSum = budCum.length > 0 ? budCum[budCum.length - 1] : 0;

  budgetMonths.forEach(bm => {
    if (!existingMonths.has(bm) && budget) {
      const bv = budget.monthly[bm];
      runningBudSum += bv.net_revenue;
      futureMonthLabels.push(bm);
      futureBudCum.push(runningBudSum);
    }
  });

  const cumulativeChartData = [
    ...months.map((m, i) => ({
      name: monthLabel(m.month),
      cy: cyCum[i],
      ly: lyCum[i],
      budget: budCum[i],
    })),
    ...futureMonthLabels.map((ml, i) => ({
      name: monthLabel(ml),
      cy: null as number | null,
      ly: null as number | null,
      budget: futureBudCum[i],
    })),
  ];

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">YTD Summary</h1>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">As of {reporting.as_of}</span>
      </div>

      <KpiGrid columns={5}>
        <KpiCard
          label="YTD Revenue"
          value={fmt(totCY.revenue)}
          tooltip={sources.ytdRevenue}
          badges={[
            { label: `vs LY ${pct(revLyPct)}`, color: badgeColor(revLyPct) },
            { label: `vs Budget ${pct(revBudPct)}`, color: badgeColor(revBudPct) },
          ]}
        />
        <KpiCard label="YTD Orders" value={fmtInt(totCY.orders)} tooltip={sources.ytdOrders} />
        <KpiCard
          label="YTD Ad Spend"
          value={fmt(totCY.ad_spend)}
          tooltip={sources.ytdAdSpend}
          badges={[
            { label: `vs LY ${pct(adLyPct)}`, color: badgeColor(adLyPct, false) },
          ]}
        />
        <KpiCard label="YTD GM%" value={totCY.gross_margin_pct?.toFixed(1) + '%'} tooltip={sources.ytdGrossMarginPct} />
        <KpiCard label="YTD MER" value={totCY.revenue && totCY.ad_spend ? ratio(totCY.revenue / totCY.ad_spend) : '\u2014'} tooltip={sources.ytdMer} />
      </KpiGrid>

      {/* Cumulative YTD Revenue Chart */}
      <ChartCard title="Cumulative YTD Revenue" height={320} tooltip={sources.cumulativeYtdRevenueChart}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={cumulativeChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#212529' }} />
            <YAxis tickFormatter={dollarFormatter} tick={{ fontSize: 10, fill: '#212529' }} />
            <Tooltip formatter={(v) => fmt(Number(v))} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="cy" name="CY Revenue" stroke="#2d6A4F" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
            <Line type="monotone" dataKey="ly" name="LY Revenue" stroke="#52796F" strokeWidth={1.5} strokeDasharray="5 4" dot={{ r: 2 }} connectNulls={false} />
            <Line type="monotone" dataKey="budget" name="Budget" stroke="#888" strokeWidth={1.5} strokeDasharray="2 3" dot={{ r: 2 }} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Monthly Revenue Table */}
      <h2 className="font-display text-lg font-semibold text-brand-neutral mt-6 md:mt-8 mb-4">Monthly Breakdown</h2>
      <div className="bg-surface-lowest rounded-xl shadow-ambient overflow-x-auto">
        <table className="w-full text-sm border-collapse min-w-[700px]">
          <thead>
            <tr className="bg-surface-low">
              <th className="text-left px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Month</th>
              <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Revenue</th>
              <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">LY</th>
              <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">YoY %</th>
              <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Budget</th>
              <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">vs Budget</th>
              <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Ad Spend</th>
              <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">MER</th>
              <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">GM%</th>
            </tr>
          </thead>
          <tbody>
            {months.map(m => {
              const yoy = calcPct(m.revenue, m.ly_revenue);
              const vsBud = calcPct(m.revenue, m.budget_revenue);
              return (
                <tr key={m.month} className="hover:bg-surface-low transition-colors">
                  <td className="px-5 py-3 font-medium">{monthLabel(m.month)}</td>
                  <td className="px-5 py-3 text-right font-semibold">{fmt(m.revenue)}</td>
                  <td className="px-5 py-3 text-right text-brand-neutral/50">{fmt(m.ly_revenue)}</td>
                  <td className={`px-5 py-3 text-right font-semibold ${yoy != null && yoy >= 0 ? 'text-brand-primary' : 'text-ns-red'}`}>
                    {pct(yoy)}
                  </td>
                  <td className="px-5 py-3 text-right text-brand-neutral/50">{fmt(m.budget_revenue)}</td>
                  <td className={`px-5 py-3 text-right font-semibold ${vsBud != null && vsBud >= 0 ? 'text-brand-primary' : 'text-ns-red'}`}>
                    {pct(vsBud)}
                  </td>
                  <td className="px-5 py-3 text-right">{fmt(m.ad_spend)}</td>
                  <td className="px-5 py-3 text-right">{ratio(m.mer)}</td>
                  <td className="px-5 py-3 text-right">{m.gross_margin_pct?.toFixed(1)}%</td>
                </tr>
              );
            })}
            {/* Totals row */}
            <tr className="bg-brand-primary/5 font-semibold">
              <td className="px-5 py-3">YTD Total</td>
              <td className="px-5 py-3 text-right font-semibold">{fmt(totCY.revenue)}</td>
              <td className="px-5 py-3 text-right text-brand-neutral/50">{fmt(totLY.revenue)}</td>
              <td className={`px-5 py-3 text-right ${revLyPct != null && revLyPct >= 0 ? 'text-brand-primary' : 'text-ns-red'}`}>
                {pct(revLyPct)}
              </td>
              <td className="px-5 py-3 text-right text-brand-neutral/50">{fmt(totBud.revenue)}</td>
              <td className={`px-5 py-3 text-right ${revBudPct != null && revBudPct >= 0 ? 'text-brand-primary' : 'text-ns-red'}`}>
                {pct(revBudPct)}
              </td>
              <td className="px-5 py-3 text-right">{fmt(totCY.ad_spend)}</td>
              <td className="px-5 py-3 text-right">{totCY.revenue && totCY.ad_spend ? ratio(totCY.revenue / totCY.ad_spend) : '\u2014'}</td>
              <td className="px-5 py-3 text-right">{totCY.gross_margin_pct?.toFixed(1)}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
