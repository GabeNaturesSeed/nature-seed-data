'use client';

import { useState } from 'react';
import { useJsonData } from '@/hooks/useJsonData';
import { ReportingData, PnlMonth } from '@/lib/types';
import CmWaterfallTable from '@/components/tables/CmWaterfallTable';
import InfoTooltip from '@/components/InfoTooltip';
import { sources } from '@/lib/sources';
import { Skeleton } from '@heroui/react';
import { fmt, monthLabel } from '@/lib/formatters';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, ReferenceLine, Cell } from 'recharts';

function buildWaterfallData(m: Partial<PnlMonth>) {
  const revenue = (m.seed_revenue ?? 0) + (m.revenue_freight ?? 0) + (m.discounts ?? 0);
  const seedCogs = m.seed_cogs ?? 0;
  const cm1 = revenue - seedCogs;
  const freight = m.cogs_freight ?? 0;
  const marketing = (m.advertising ?? 0) + (m.development ?? 0);
  const cm2 = cm1 - freight - marketing;
  const ga = m.total_ga ?? 0;
  const netIncome = cm2 - ga;

  return [
    { name: 'Revenue', value: revenue, total: revenue, type: 'start' as const },
    { name: 'Seed COGS', value: -seedCogs, total: cm1, type: 'cost' as const },
    { name: 'CM1', value: cm1, total: cm1, type: 'subtotal' as const },
    { name: 'Freight', value: -freight, total: cm1 - freight, type: 'cost' as const },
    { name: 'Marketing', value: -marketing, total: cm2, type: 'cost' as const },
    { name: 'CM2', value: cm2, total: cm2, type: 'subtotal' as const },
    { name: 'G&A', value: -ga, total: netIncome, type: 'cost' as const },
    { name: 'Net Income', value: netIncome, total: netIncome, type: 'end' as const },
  ];
}

const barColor: Record<'start' | 'cost' | 'subtotal' | 'end', string> = {
  start: '#3a7a45',
  cost: '#c96a2e',
  subtotal: '#5a8fb4',
  end: '#5b8a3a',
};

export default function CmWaterfallPage() {
  const { data, loading } = useJsonData<ReportingData>('reporting');
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <Skeleton className="h-96 rounded-xl" />
      </div>
    );
  }

  if (!data) return <p className="text-brand-neutral/50">CM data unavailable</p>;

  const months = data.pnl.months;
  const activeMonthKey = selectedMonth ?? months[months.length - 1]?.month;
  const activeMonth = months.find(m => m.month === activeMonthKey) ?? months[months.length - 1];
  const chartData = buildWaterfallData(activeMonth);

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <div>
          <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral flex items-center gap-2">
            <span>Contribution Margin Waterfall</span>
            <InfoTooltip content={sources.cmWaterfall} size={15} />
          </h1>
          <p className="text-[11px] md:text-xs text-brand-neutral/60 mt-1">
            Revenue → CM1 (after seed COGS) → CM2 (after freight + marketing) → Net Income (after G&amp;A)
          </p>
        </div>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">As of {data.as_of}</span>
      </div>

      {/* Waterfall chart section */}
      <div className="bg-surface-lowest rounded-xl shadow-ambient p-5 md:p-6 mb-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h2 className="text-sm font-semibold text-brand-neutral">Waterfall — {monthLabel(activeMonth.month)}</h2>
          <div className="flex flex-wrap gap-1.5">
            {months.map(m => (
              <button
                key={m.month}
                onClick={() => setSelectedMonth(m.month)}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                  m.month === activeMonthKey
                    ? 'bg-brand-primary text-white border-brand-primary'
                    : 'bg-surface-lowest text-brand-neutral/70 border-brand-neutral/20 hover:border-brand-primary/50'
                }`}
              >
                {monthLabel(m.month)}
              </button>
            ))}
          </div>
        </div>
        <div className="h-80">
          <ResponsiveContainer>
            <BarChart data={chartData} margin={{ top: 16, right: 16, left: 8, bottom: 8 }}>
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#2c3e2b' }} />
              <YAxis
                tick={{ fontSize: 11, fill: '#2c3e2b' }}
                tickFormatter={v => '$' + (v / 1000).toFixed(0) + 'K'}
              />
              <ReferenceLine y={0} stroke="#999" strokeDasharray="2 2" />
              <Tooltip
                formatter={(value) => {
                  const n = typeof value === 'number' ? value : Number(value);
                  return [fmt(Math.abs(n)), n < 0 ? 'Cost' : 'Value'];
                }}
                cursor={{ fill: 'rgba(0,0,0,0.03)' }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {chartData.map((d, i) => (
                  <Cell key={i} fill={barColor[d.type]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-wrap gap-4 text-[11px] text-brand-neutral/70 mt-2">
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded" style={{ background: barColor.start }} />Revenue</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded" style={{ background: barColor.cost }} />Deductions</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded" style={{ background: barColor.subtotal }} />CM subtotals</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded" style={{ background: barColor.end }} />Net Income</span>
        </div>
      </div>

      {/* Detail table */}
      <CmWaterfallTable months={data.pnl.months} ytd={data.pnl.ytd} />

      <p className="text-[11px] text-brand-neutral/60 mt-4 max-w-3xl">
        <strong>Note on OPEX (G&amp;A):</strong> This waterfall deducts only G&amp;A (salaries, professional fees, insurance, T&amp;E, utilities, corporate allocation). It excludes Production/Warehouse and non-ad SMA costs, which still appear on the full P&amp;L Statement. Net Income here reflects contribution after G&amp;A only and will differ from the P&amp;L bottom line.
      </p>
    </div>
  );
}
