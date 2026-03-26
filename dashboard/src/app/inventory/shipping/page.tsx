'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { ShippingData, ReportingData } from '@/lib/types';
import { fmt, fmtInt, pctPlain } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import ChartCard from '@/components/charts/ChartCard';
import { Skeleton } from '@heroui/react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';

export default function ShippingPage() {
  const { data, loading } = useJsonData<ShippingData>('shipping');
  const { data: reporting } = useJsonData<ReportingData>('reporting');

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      </div>
    );
  }

  if (!data) return <p className="text-brand-neutral/50">Shipping data unavailable</p>;

  const { mtd, ytd, carriers, weekly_cost_per_lb } = data;

  // Build weekly chart data
  const upsData = weekly_cost_per_lb['UPS'];
  const uspsData = weekly_cost_per_lb['USPS'];
  const fedexData = weekly_cost_per_lb['FEDEX'];

  const uspsMap: Record<string, number> = {};
  const fedexMap: Record<string, number> = {};
  uspsData?.weeks.forEach((w, i) => { uspsMap[w] = uspsData.values[i]; });
  fedexData?.weeks.forEach((w, i) => { fedexMap[w] = fedexData.values[i]; });

  const weeklyChartData = (upsData?.weeks ?? []).map((w, i) => ({
    name: w,
    UPS: upsData.values[i],
    USPS: uspsMap[w] ?? null,
    FedEx: fedexMap[w] ?? null,
  }));

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">Shipping Insights</h1>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">As of {data.as_of}</span>
      </div>

      {/* MTD KPIs */}
      <h2 className="font-display text-lg font-semibold text-brand-neutral mb-4">Month to Date</h2>
      <KpiGrid columns={5}>
        <KpiCard label="Collected" value={fmt(mtd.shipping_collected)} />
        <KpiCard label="Paid" value={fmt(mtd.shipping_paid)} />
        <KpiCard
          label="Net (Gap)"
          value={fmt(mtd.shipping_net)}
          badges={[{ label: 'Customer absorbs gap', color: 'danger' }]}
        />
        <KpiCard label="Shipments" value={fmtInt(mtd.shipment_count)} />
        <KpiCard label="Avg Cost/Order" value={fmt(mtd.avg_cost_per_order)} />
      </KpiGrid>

      {/* YTD KPIs */}
      <h2 className="font-display text-lg font-semibold text-brand-neutral mb-4">Year to Date</h2>
      <KpiGrid columns={5}>
        <KpiCard label="Collected" value={fmt(ytd.shipping_collected)} />
        <KpiCard label="Paid" value={fmt(ytd.shipping_paid)} />
        <KpiCard label="Net (Gap)" value={fmt(ytd.shipping_net)} badges={[{ label: 'Total absorbed', color: 'danger' }]} />
        <KpiCard label="Shipments" value={fmtInt(ytd.shipment_count)} />
        <KpiCard label="Avg Cost/Order" value={fmt(ytd.avg_cost_per_order)} />
      </KpiGrid>

      {/* Carrier Breakdown */}
      <h2 className="font-display text-lg font-semibold text-brand-neutral mb-4">Carrier Breakdown (YTD)</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-8">
        {carriers.map(c => (
          <div key={c.carrier} className="bg-surface-lowest rounded-xl shadow-ambient p-5">
            <p className="font-display text-lg font-semibold mb-3 text-brand-neutral">{c.carrier}</p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-brand-neutral/50">Total Paid</span>
                <span className="font-semibold">{fmt(c.total_paid)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-brand-neutral/50">Shipments</span>
                <span>{fmtInt(c.shipment_count)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-brand-neutral/50">% of Volume</span>
                <span>{pctPlain(c.pct_of_shipments)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-brand-neutral/50">Avg/Shipment</span>
                <span>{fmt(c.avg_cost_per_shipment)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Weekly Cost Chart */}
      <ChartCard title="Weekly Avg Cost per Shipment by Carrier" height={300}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={weeklyChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
            <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#212529' }} />
            <YAxis tickFormatter={v => '$' + v} tick={{ fontSize: 10, fill: '#212529' }} />
            <Tooltip formatter={(v) => '$' + Number(v).toFixed(2)} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="UPS" stroke="#5B3200" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
            <Line type="monotone" dataKey="USPS" stroke="#004B87" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
            <Line type="monotone" dataKey="FedEx" stroke="#4D148C" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Shippo vs Finance Actuals Comparison */}
      {reporting?.pnl?.months && (() => {
        const pnlMonths = reporting.pnl.months;
        const ytdMonths = reporting.ytd?.months ?? [];

        // Build comparison rows
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const compRows = pnlMonths.map((pm: any) => {
          const mk = String(pm.month ?? '');
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const ytdM: any = ytdMonths.find((m: any) => m.month === mk);
          const shippo = Number(pm.shippo_freight ?? ytdM?.shipping ?? 0);
          const financeFreight = Number(pm.cogs_freight ?? 0);
          const revenue = Number(ytdM?.revenue ?? 0);
          const cogs = Number(ytdM?.cogs ?? 0);
          const adSpend = Number(ytdM?.ad_spend ?? 0);
          const grossProfit = revenue - cogs;
          const cm1 = grossProfit - adSpend;
          const diff = shippo - financeFreight;
          const shippoPctCm1 = cm1 > 0 ? (shippo / cm1 * 100) : 0;
          const financePctCm1 = cm1 > 0 ? (financeFreight / cm1 * 100) : 0;

          return { month: mk, shippo, financeFreight, diff, cm1, shippoPctCm1, financePctCm1, hasActuals: pm.source === 'actuals' };
        });

        // YTD totals
        const ytdShippo = compRows.reduce((s: number, r: { shippo: number }) => s + r.shippo, 0);
        const ytdFinance = compRows.reduce((s: number, r: { financeFreight: number }) => s + r.financeFreight, 0);
        const ytdCm1 = compRows.reduce((s: number, r: { cm1: number }) => s + r.cm1, 0);
        const ytdDiff = ytdShippo - ytdFinance;

        const monthLabel = (m: string) => {
          const d = new Date(m + '-02');
          return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        };

        return (
          <div className="mt-10">
            <h2 className="font-display text-lg font-semibold text-brand-neutral mb-2">Shippo Charges vs Finance P&L Freight</h2>
            <p className="text-sm text-brand-neutral/50 mb-4">
              Comparing what Shippo billed us vs what finance recorded as COGS Freight on the P&L, and each as a % of CM1.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left" style={{ background: '#2d6A4F' }}>
                    <th className="text-white py-3 px-4 font-medium rounded-tl-xl">Month</th>
                    <th className="text-white py-3 px-4 font-medium text-right">Shippo Charged</th>
                    <th className="text-white py-3 px-4 font-medium text-right">Finance P&L</th>
                    <th className="text-white py-3 px-4 font-medium text-right">Difference</th>
                    <th className="text-white py-3 px-4 font-medium text-right">CM1</th>
                    <th className="text-white py-3 px-4 font-medium text-right">Shippo % of CM1</th>
                    <th className="text-white py-3 px-4 font-medium text-right rounded-tr-xl">Finance % of CM1</th>
                  </tr>
                </thead>
                <tbody>
                  {compRows.map((r: { month: string; shippo: number; financeFreight: number; diff: number; cm1: number; shippoPctCm1: number; financePctCm1: number; hasActuals: boolean }, i: number) => (
                    <tr key={r.month} className={i % 2 === 0 ? 'bg-surface-lowest' : 'bg-surface-low'}>
                      <td className="py-3 px-4 font-medium">{monthLabel(r.month)}</td>
                      <td className="py-3 px-4 text-right font-semibold">{fmt(r.shippo)}</td>
                      <td className="py-3 px-4 text-right">
                        {r.hasActuals ? (
                          <span className="font-semibold">{fmt(r.financeFreight)}</span>
                        ) : (
                          <span className="text-brand-neutral/40 italic">Pending</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {r.hasActuals ? (
                          <span className={r.diff > 0 ? 'text-red-600 font-semibold' : 'text-brand-primary font-semibold'}>
                            {r.diff > 0 ? '+' : ''}{fmt(r.diff)}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="py-3 px-4 text-right text-brand-neutral/60">{fmt(r.cm1)}</td>
                      <td className="py-3 px-4 text-right">
                        <span className={r.shippoPctCm1 > 60 ? 'text-red-600 font-semibold' : r.shippoPctCm1 > 40 ? 'text-amber-600' : 'text-brand-primary'}>
                          {r.shippoPctCm1.toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {r.hasActuals ? (
                          <span className={r.financePctCm1 > 60 ? 'text-red-600 font-semibold' : r.financePctCm1 > 40 ? 'text-amber-600' : 'text-brand-primary'}>
                            {r.financePctCm1.toFixed(1)}%
                          </span>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                  {/* YTD Total Row */}
                  <tr className="border-t-2" style={{ borderColor: 'rgba(191,201,193,0.3)' }}>
                    <td className="py-3 px-4 font-display font-bold text-brand-neutral">YTD Total</td>
                    <td className="py-3 px-4 text-right font-bold text-lg">{fmt(ytdShippo)}</td>
                    <td className="py-3 px-4 text-right font-bold text-lg">{fmt(ytdFinance)}</td>
                    <td className="py-3 px-4 text-right">
                      <span className={ytdDiff > 0 ? 'text-red-600 font-bold text-lg' : 'text-brand-primary font-bold'}>
                        {ytdDiff > 0 ? '+' : ''}{fmt(ytdDiff)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-bold">{fmt(ytdCm1)}</td>
                    <td className="py-3 px-4 text-right font-bold">
                      {ytdCm1 > 0 ? (ytdShippo / ytdCm1 * 100).toFixed(1) + '%' : '—'}
                    </td>
                    <td className="py-3 px-4 text-right font-bold">
                      {ytdCm1 > 0 ? (ytdFinance / ytdCm1 * 100).toFixed(1) + '%' : '—'}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="text-xs text-brand-neutral/40 mt-3">
              Shippo = actual label charges from Shippo API. Finance P&L = COGS Freight from finance actuals CSV (Jan/Feb uploaded, Mar pending).
              Difference shows how much more/less Shippo charged vs what appeared on the P&L. Color coding: red &gt;60% of CM1, amber &gt;40%.
            </p>
          </div>
        );
      })()}
    </div>
  );
}
