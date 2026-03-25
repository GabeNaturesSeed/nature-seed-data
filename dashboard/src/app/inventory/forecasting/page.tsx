'use client';

import { useMemo } from 'react';
import { useJsonData } from '@/hooks/useJsonData';
import { InventoryData } from '@/lib/types';
import { fmtInt } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import { Skeleton, Chip } from '@heroui/react';

export default function ForecastingPage() {
  const { data, loading } = useJsonData<InventoryData>('inventory');

  const forecastItems = useMemo(() => {
    if (!data) return [];
    return [...data.items]
      .filter(i => i.daily_velocity > 0)
      .sort((a, b) => a.days_remaining - b.days_remaining);
  }, [data]);

  const urgentCount = forecastItems.filter(i => i.days_remaining <= 30).length;
  const warningCount = forecastItems.filter(i => i.days_remaining > 30 && i.days_remaining <= 90).length;

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (!data) return <p className="text-brand-neutral/50">Inventory data unavailable</p>;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">Inventory Forecasting</h1>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">As of {data.as_of}</span>
      </div>

      <KpiGrid columns={3}>
        <KpiCard label="Active SKUs (velocity > 0)" value={fmtInt(forecastItems.length)} />
        <KpiCard label="Stockout in 30d" value={fmtInt(urgentCount)} badges={urgentCount > 0 ? [{ label: 'Reorder now', color: 'danger' }] : []} />
        <KpiCard label="Stockout in 30-90d" value={fmtInt(warningCount)} badges={warningCount > 0 ? [{ label: 'Plan reorder', color: 'warning' }] : []} />
      </KpiGrid>

      <div className="bg-surface-lowest rounded-xl shadow-ambient overflow-x-auto">
        <table className="w-full text-sm border-collapse min-w-[900px]">
          <thead>
            <tr className="bg-surface-low">
              <th className="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">SKU</th>
              <th className="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Product</th>
              <th className="px-5 py-3.5 text-right text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Qty</th>
              <th className="px-5 py-3.5 text-right text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Daily Vel.</th>
              <th className="px-5 py-3.5 text-right text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Days Left</th>
              <th className="px-5 py-3.5 text-right text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Q1 Need</th>
              <th className="px-5 py-3.5 text-right text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Q2 Need</th>
              <th className="px-5 py-3.5 text-right text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Surplus/Gap</th>
              <th className="px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {forecastItems.map(item => (
              <tr key={item.sku} className="hover:bg-surface-low transition-colors">
                <td className="px-5 py-2.5 font-mono text-xs">{item.sku}</td>
                <td className="px-5 py-2.5">{item.name}</td>
                <td className="px-5 py-2.5 text-right">{fmtInt(item.qty)}</td>
                <td className="px-5 py-2.5 text-right">{item.daily_velocity.toFixed(1)}</td>
                <td className={`px-5 py-2.5 text-right font-semibold ${item.days_remaining <= 30 ? 'text-ns-red' : item.days_remaining <= 90 ? 'text-ns-yellow' : ''}`}>
                  {item.days_remaining >= 9999 ? '999+' : fmtInt(item.days_remaining)}
                </td>
                <td className="px-5 py-2.5 text-right">{item.q1_need.toFixed(1)}</td>
                <td className="px-5 py-2.5 text-right">{item.q2_need.toFixed(1)}</td>
                <td className={`px-5 py-2.5 text-right font-semibold ${item.surplus_gap < 0 ? 'text-ns-red' : 'text-brand-primary'}`}>
                  {item.surplus_gap.toFixed(1)}
                </td>
                <td className="px-5 py-2.5">
                  <Chip size="sm" variant="soft" color={item.status === 'red' ? 'danger' : item.status === 'yellow' ? 'warning' : 'success'}>
                    {item.status === 'red' ? 'Critical' : item.status === 'yellow' ? 'Low' : 'OK'}
                  </Chip>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
