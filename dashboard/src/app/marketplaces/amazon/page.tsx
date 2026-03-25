'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { AmazonData } from '@/lib/types';
import { fmt, fmtInt } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import ChartCard from '@/components/charts/ChartCard';
import { Skeleton, Chip } from '@heroui/react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';

export default function AmazonPage() {
  const { data, loading } = useJsonData<AmazonData>('amazon');

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

  if (!data) return <p className="text-brand-neutral/50">Amazon data unavailable</p>;

  const { last_30d, daily, account_health } = data;

  const chartData = daily.map(d => ({
    name: new Date(d.date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    revenue: d.revenue,
    orders: d.orders,
  }));

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">Amazon</h1>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">As of {data.as_of}</span>
      </div>

      <KpiGrid columns={3}>
        <KpiCard label="Revenue (30d)" value={fmt(last_30d.revenue)} />
        <KpiCard label="Orders (30d)" value={fmtInt(last_30d.orders)} />
        <KpiCard label="AOV" value={fmt(last_30d.aov)} />
      </KpiGrid>

      {/* Account Health */}
      <h2 className="font-display text-lg font-semibold text-brand-neutral mb-4">Account Health</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-6 md:mb-8">
        <div className="bg-surface-lowest rounded-xl shadow-ambient p-5 text-center">
          <p className="text-xs text-brand-neutral/50 uppercase mb-2">Status</p>
          <Chip color={account_health.status === 'Good' ? 'success' : 'danger'} variant="soft">
            {account_health.status}
          </Chip>
        </div>
        <div className="bg-surface-lowest rounded-xl shadow-ambient p-5 text-center">
          <p className="text-xs text-brand-neutral/50 uppercase mb-2">Defect Rate</p>
          <p className="text-xl font-semibold text-brand-neutral">{account_health.defect_rate}%</p>
        </div>
        <div className="bg-surface-lowest rounded-xl shadow-ambient p-5 text-center">
          <p className="text-xs text-brand-neutral/50 uppercase mb-2">Cancellation</p>
          <p className="text-xl font-semibold text-brand-neutral">{account_health.cancellation_rate}%</p>
        </div>
        <div className="bg-surface-lowest rounded-xl shadow-ambient p-5 text-center">
          <p className="text-xs text-brand-neutral/50 uppercase mb-2">Late Shipment</p>
          <p className="text-xl font-semibold text-brand-neutral">{account_health.late_shipment_rate}%</p>
        </div>
      </div>

      {/* Daily Revenue Chart */}
      <ChartCard title="Daily Revenue (30d)" height={280}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
            <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#212529' }} interval={2} />
            <YAxis tickFormatter={v => '$' + v} tick={{ fontSize: 10, fill: '#212529' }} />
            <Tooltip formatter={(v) => fmt(Number(v))} />
            <Bar dataKey="revenue" fill="#FF9900" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {data.issues && data.issues.length > 0 && (
        <div className="mt-8">
          <h2 className="font-display text-lg font-semibold text-brand-neutral mb-4">Issues</h2>
          {data.issues.map((issue, i) => (
            <div key={i} className="bg-ns-red/5 rounded-xl shadow-ambient mb-2 p-4 text-sm text-ns-red">
              {String(issue)}
            </div>
          ))}
        </div>
      )}

      {(!data.issues || data.issues.length === 0) && (
        <div className="bg-brand-primary/5 rounded-xl shadow-ambient mt-8 p-4 text-sm text-brand-primary">
          No active issues
        </div>
      )}
    </div>
  );
}
