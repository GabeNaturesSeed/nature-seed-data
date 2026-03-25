'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { ShippingData } from '@/lib/types';
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

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <div className="grid grid-cols-3 gap-6">
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
      <div className="flex items-baseline justify-between mb-8">
        <h1 className="text-2xl font-display font-bold text-brand-neutral">Shipping Insights</h1>
        <span className="text-xs text-brand-neutral/50">As of {data.as_of}</span>
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
    </div>
  );
}
