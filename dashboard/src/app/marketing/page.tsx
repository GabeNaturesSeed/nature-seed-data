'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { MarketingData } from '@/lib/types';
import { fmt, fmtInt, ratio, pctPlain, monthLabel, shortDate } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import ChartCard from '@/components/charts/ChartCard';
import { Skeleton, Accordion, AccordionItem, AccordionHeading, AccordionTrigger, AccordionPanel, AccordionBody } from '@heroui/react';
import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';

export default function MarketingPage() {
  const { data, loading } = useJsonData<MarketingData>('marketing');

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <div className="grid grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      </div>
    );
  }

  if (!data) return <p className="text-brand-neutral/50">Marketing data unavailable</p>;

  const w = data.widgets;
  const channels = data.channels;

  // Monthly chart data
  const monthlyChartData = data.monthly_12m.map(m => ({
    name: monthLabel(m.month),
    adSpend: m.ad_spend,
    wcRevenue: m.wc_revenue,
    mer: m.mer,
  }));

  // Daily 90d chart data (sample every 3 days for readability)
  const dailyChartData = data.daily_90d
    .filter((_, i) => i % 3 === 0 || i === data.daily_90d.length - 1)
    .map(d => ({
      name: shortDate(d.date),
      adSpend: d.ad_spend,
      wcRevenue: d.wc_revenue,
      mer: d.mer,
    }));

  return (
    <div>
      <div className="flex items-baseline justify-between mb-8">
        <h1 className="text-2xl font-display font-bold text-brand-neutral">Marketing Performance</h1>
        <span className="text-xs text-brand-neutral/50">{data.period_start} to {data.period_end}</span>
      </div>

      {/* LTV / CAC Widgets */}
      <KpiGrid columns={4}>
        <KpiCard label="12m LTV" value={fmt(w.ltv_12m)} />
        <KpiCard label="CAC" value={fmt(w.cac)} note={`Max BE: ${fmt(w.max_cac_breakeven)}`} />
        <KpiCard label="nCAC" value={fmt(w.ncac)} note={`Max 20% margin: ${fmt(w.max_cac_20pct)}`} />
        <KpiCard label="LTV:CAC" value={ratio(w.ltv_cac_ratio)} badges={[
          { label: `${w.payback_months} mo payback`, color: w.payback_months <= 3 ? 'success' : 'warning' }
        ]} />
      </KpiGrid>

      {/* Channel ROAS */}
      <h2 className="font-display text-lg font-semibold text-brand-neutral mb-4">Channel Performance</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {/* CTV (Vibe.co) Card */}
        {(() => {
          const ctvMonthlySpend = data.monthly_12m.reduce((sum, m) => sum + (m.ad_spend - m.ad_spend_google), 0);
          const ctvLast30d = data.daily_90d.slice(-30).reduce((sum, d) => sum + (d.ad_spend - d.ad_spend_google), 0);
          return (
            <div className="bg-surface-lowest rounded-xl shadow-ambient p-5">
              <p className="text-sm font-semibold mb-3 text-brand-neutral">CTV (Vibe.co)</p>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-brand-neutral/50">12m Spend</span>
                  <span className="font-semibold">{fmt(ctvMonthlySpend)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-brand-neutral/50">Last 30d Spend</span>
                  <span>{fmt(ctvLast30d)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-brand-neutral/50">% of Total Ad Spend</span>
                  <span>{data.total_ad_spend > 0 ? ((ctvMonthlySpend / data.total_ad_spend) * 100).toFixed(1) + '%' : '\u2014'}</span>
                </div>
                {ctvMonthlySpend === 0 && ctvLast30d === 0 && (
                  <p className="text-xs text-ns-yellow mt-2">CTV data pending — Supabase constraint fix needed</p>
                )}
              </div>
            </div>
          );
        })()}
        {channels.map(ch => (
          <div key={ch.name} className="bg-surface-lowest rounded-xl shadow-ambient p-5">
            <p className="text-sm font-semibold mb-3 text-brand-neutral">{ch.name}</p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-brand-neutral/50">ROAS</span>
                <span className="font-semibold">{ratio(ch.roas)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-brand-neutral/50">CAC</span>
                <span>{fmt(ch.cac)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-brand-neutral/50">nCAC</span>
                <span>{fmt(ch.ncac)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-brand-neutral/50">LTV</span>
                <span>{fmt(ch.ltv)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-brand-neutral/50">Revenue %</span>
                <span>{pctPlain(ch.revenue_contribution_pct)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-brand-neutral/50">Payback</span>
                <span>{ch.payback_months} months</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary stats */}
      <KpiGrid columns={4}>
        <KpiCard label="Total Customers (12m)" value={fmtInt(data.total_customers)} />
        <KpiCard label="New Customers" value={fmtInt(data.new_customers)} />
        <KpiCard label="Returning" value={fmtInt(data.returning_customers)} />
        <KpiCard label="Contribution Margin" value={pctPlain(w.contribution_margin * 100)} />
      </KpiGrid>

      {/* 12-Month Chart */}
      <ChartCard title="12-Month Revenue vs Ad Spend" height={320}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={monthlyChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#212529' }} />
            <YAxis yAxisId="left" tickFormatter={v => '$' + (v / 1000).toFixed(0) + 'K'} tick={{ fontSize: 10, fill: '#212529' }} />
            <YAxis yAxisId="right" orientation="right" tickFormatter={v => v + 'x'} tick={{ fontSize: 10, fill: '#212529' }} domain={[0, 'auto']} />
            <Tooltip formatter={(v, name) => name === 'MER' ? ratio(Number(v)) : fmt(Number(v))} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar yAxisId="left" dataKey="adSpend" name="Ad Spend" fill="#c96a2e" opacity={0.7} radius={[3, 3, 0, 0]} />
            <Line yAxisId="left" type="monotone" dataKey="wcRevenue" name="WC Revenue" stroke="#2d6A4F" strokeWidth={2} dot={{ r: 3 }} />
            <Line yAxisId="right" type="monotone" dataKey="mer" name="MER" stroke="#52796F" strokeWidth={1.5} strokeDasharray="3 3" dot={{ r: 2 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* 90-Day Detail Tables in Accordion */}
      <Accordion className="mt-8">
        <AccordionItem>
          <AccordionHeading>
            <AccordionTrigger className="font-display text-lg font-semibold text-brand-neutral">
              90-Day Daily Detail
            </AccordionTrigger>
          </AccordionHeading>
          <AccordionPanel>
            <AccordionBody>
              <div className="bg-surface-lowest rounded-xl shadow-ambient overflow-x-auto">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="bg-surface-low">
                      <th className="px-4 py-2.5 text-left text-brand-neutral/50 font-semibold">Date</th>
                      <th className="px-4 py-2.5 text-right text-brand-neutral/50 font-semibold">Ad Spend</th>
                      <th className="px-4 py-2.5 text-right text-brand-neutral/50 font-semibold">Channel Rev</th>
                      <th className="px-4 py-2.5 text-right text-brand-neutral/50 font-semibold">WC Revenue</th>
                      <th className="px-4 py-2.5 text-right text-brand-neutral/50 font-semibold">MER</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.daily_90d.map(d => (
                      <tr key={d.date} className="hover:bg-surface-low transition-colors">
                        <td className="px-4 py-1.5">{shortDate(d.date)}</td>
                        <td className="px-4 py-1.5 text-right">{fmt(d.ad_spend)}</td>
                        <td className="px-4 py-1.5 text-right">{fmt(d.channel_revenue)}</td>
                        <td className="px-4 py-1.5 text-right">{fmt(d.wc_revenue)}</td>
                        <td className="px-4 py-1.5 text-right">{d.mer != null ? ratio(d.mer) : '\u2014'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </AccordionBody>
          </AccordionPanel>
        </AccordionItem>

        <AccordionItem>
          <AccordionHeading>
            <AccordionTrigger className="font-display text-lg font-semibold text-brand-neutral">
              12-Month Monthly Detail
            </AccordionTrigger>
          </AccordionHeading>
          <AccordionPanel>
            <AccordionBody>
              <div className="bg-surface-lowest rounded-xl shadow-ambient overflow-x-auto">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="bg-surface-low">
                      <th className="px-4 py-2.5 text-left text-brand-neutral/50 font-semibold">Month</th>
                      <th className="px-4 py-2.5 text-right text-brand-neutral/50 font-semibold">Ad Spend</th>
                      <th className="px-4 py-2.5 text-right text-brand-neutral/50 font-semibold">Channel Rev</th>
                      <th className="px-4 py-2.5 text-right text-brand-neutral/50 font-semibold">WC Revenue</th>
                      <th className="px-4 py-2.5 text-right text-brand-neutral/50 font-semibold">MER</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.monthly_12m.map(m => (
                      <tr key={m.month} className="hover:bg-surface-low transition-colors">
                        <td className="px-4 py-1.5">{monthLabel(m.month)}</td>
                        <td className="px-4 py-1.5 text-right">{fmt(m.ad_spend)}</td>
                        <td className="px-4 py-1.5 text-right">{fmt(m.channel_revenue)}</td>
                        <td className="px-4 py-1.5 text-right">{fmt(m.wc_revenue)}</td>
                        <td className="px-4 py-1.5 text-right">{ratio(m.mer)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </AccordionBody>
          </AccordionPanel>
        </AccordionItem>
      </Accordion>
    </div>
  );
}
