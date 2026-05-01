'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { HealthData } from '@/lib/types';
import { fmtInt } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import ChartCard from '@/components/charts/ChartCard';
import { Skeleton } from '@heroui/react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';

function formatHour(hour: number): string {
  if (hour === 0) return '12am';
  if (hour === 12) return '12pm';
  if (hour < 12) return `${hour}am`;
  return `${hour - 12}pm`;
}


function noResultColor(rate: number): string {
  if (rate < 5) return 'text-brand-primary';
  if (rate <= 10) return 'text-ns-yellow';
  return 'text-ns-red';
}

export default function WebsiteHealthPage() {
  const { data, loading } = useJsonData<HealthData>('health');

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-56 rounded-xl" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
        <Skeleton className="h-72 rounded-xl" />
      </div>
    );
  }

  if (!data) return <p className="text-brand-neutral/50">Website health data unavailable</p>;

  const { order_velocity, search_health, server } = data;

  // Chart data
  const hourlyChartData = order_velocity.hourly.map(h => ({
    name: formatHour(h.hour),
    Today: h.today,
    'Last Week': h.last_week,
  }));

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">Website Health</h1>
        <span className="text-xs text-brand-neutral/50">
          As of {new Date(data.as_of).toLocaleString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
            hour: 'numeric', minute: '2-digit',
          })}
        </span>
      </div>

      {/* ── Section 1: Order Velocity ── */}
      <ChartCard title="Order Velocity — Hour by Hour" height={320}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={hourlyChartData} barCategoryGap="20%">
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#212529' }} interval={1} />
            <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: '#212529' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: 'none',
                borderRadius: '0.75rem',
                boxShadow: '0 4px 32px rgba(24, 28, 32, 0.06)',
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="Today" fill="#2d6A4F" radius={[3, 3, 0, 0]} />
            <Bar dataKey="Last Week" fill="#52796F" opacity={0.35} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="flex flex-col sm:flex-row gap-4 md:gap-6 mt-4 mb-6 md:mb-8">
        <div className="bg-surface-lowest rounded-xl shadow-ambient p-5 flex-1">
          <p className="text-xs uppercase tracking-wider text-brand-neutral/50 mb-1">Today Total</p>
          <p className="text-3xl font-semibold text-brand-neutral">{fmtInt(order_velocity.today_total)}</p>
          <p className="text-xs text-brand-neutral/50">{order_velocity.today_label}</p>
        </div>
        <div className="bg-surface-lowest rounded-xl shadow-ambient p-5 flex-1">
          <p className="text-xs uppercase tracking-wider text-brand-neutral/50 mb-1">Same Day Last Week</p>
          <p className="text-3xl font-semibold text-brand-neutral">{fmtInt(order_velocity.last_week_total)}</p>
          {order_velocity.last_week_total > 0 && (
            <p className={`text-xs font-medium ${
              order_velocity.today_total >= order_velocity.last_week_total ? 'text-brand-primary' : 'text-ns-red'
            }`}>
              {order_velocity.today_total >= order_velocity.last_week_total ? '+' : ''}
              {((order_velocity.today_total - order_velocity.last_week_total) / order_velocity.last_week_total * 100).toFixed(1)}% vs last week
            </p>
          )}
        </div>
      </div>

      {/* ── Section 3: Search Health ── */}
      <h2 className="font-display text-lg font-semibold text-brand-neutral mb-4">Search Health</h2>

      <KpiGrid columns={3}>
        <KpiCard label="Total Searches (24h)" value={fmtInt(search_health.total_searches_24h)} />
        <div className="bg-surface-lowest rounded-xl shadow-ambient p-5">
          <p className="text-xs uppercase tracking-wider text-brand-neutral/50 mb-2">No-Result Rate</p>
          <p className={`text-3xl font-semibold mb-1 ${noResultColor(search_health.no_result_rate)}`}>
            {search_health.no_result_rate.toFixed(1)}%
          </p>
          <p className="text-xs text-brand-neutral/50">
            {search_health.no_result_rate < 5 ? 'Good' : search_health.no_result_rate <= 10 ? 'Needs attention' : 'Critical'}
          </p>
        </div>
        <KpiCard label="No-Result Searches" value={fmtInt(search_health.no_result_searches)} />
      </KpiGrid>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 mb-6 md:mb-8">
        {/* Top Searches */}
        <div className="bg-surface-lowest rounded-xl shadow-ambient overflow-hidden">
          <div className="px-5 pt-5 pb-3">
            <h3 className="font-display text-base font-semibold text-brand-neutral">Top 10 Searches</h3>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-surface-low">
                <th className="px-5 py-2.5 text-left text-brand-neutral/50 font-semibold">Query</th>
                <th className="px-5 py-2.5 text-right text-brand-neutral/50 font-semibold">Count</th>
              </tr>
            </thead>
            <tbody>
              {search_health.top_searches.length > 0 ? (
                search_health.top_searches.map((s, i) => (
                  <tr key={i} className="hover:bg-surface-low transition-colors">
                    <td className="px-5 py-2 text-brand-neutral">{s.query}</td>
                    <td className="px-5 py-2 text-right font-medium">{fmtInt(s.count)}</td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={2} className="px-5 py-4 text-center text-brand-neutral/40 text-xs">No search data available</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Top No-Result Queries */}
        <div className="bg-surface-lowest rounded-xl shadow-ambient overflow-hidden">
          <div className="px-5 pt-5 pb-3">
            <h3 className="font-display text-base font-semibold text-brand-neutral">Top No-Result Queries</h3>
            <p className="text-xs text-brand-neutral/50 mt-1">These need synonyms or products</p>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-surface-low">
                <th className="px-5 py-2.5 text-left text-brand-neutral/50 font-semibold">Query</th>
                <th className="px-5 py-2.5 text-right text-brand-neutral/50 font-semibold">Count</th>
              </tr>
            </thead>
            <tbody>
              {search_health.top_no_results.map((s, i) => (
                <tr key={i} className="hover:bg-surface-low transition-colors">
                  <td className="px-5 py-2 text-ns-red">{s.query}</td>
                  <td className="px-5 py-2 text-right font-medium">{fmtInt(s.count)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Section 4: Server Health ── */}
      <h2 className="font-display text-lg font-semibold text-brand-neutral mb-4">Server Health</h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 md:mb-8">
        {Object.entries(server).map(([key, value]) => (
          <div key={key} className="bg-surface-lowest rounded-xl shadow-ambient p-5">
            <p className="text-xs uppercase tracking-wider text-brand-neutral/50 mb-2">
              {key.replace(/_/g, ' ')}
            </p>
            <p className="text-lg font-semibold text-brand-neutral">{value != null ? String(value) : '\u2014'}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
