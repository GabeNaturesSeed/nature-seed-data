'use client';

import { useState, useMemo } from 'react';
import { useJsonData } from '@/hooks/useJsonData';
import { InventoryData } from '@/lib/types';
import { fmtInt } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import { Skeleton, Chip } from '@heroui/react';

type SortKey = 'sku' | 'name' | 'qty' | 'daily_velocity' | 'days_remaining' | 'status';
type SortDir = 'asc' | 'desc';

export default function InventoryPage() {
  const { data, loading } = useJsonData<InventoryData>('inventory');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('days_remaining');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const items = data?.items ?? [];

  const counts = useMemo(() => {
    let red = 0, yellow = 0, ok = 0;
    items.forEach(item => {
      if (item.status === 'red') red++;
      else if (item.status === 'yellow') yellow++;
      else ok++;
    });
    return { red, yellow, ok, total: items.length };
  }, [items]);

  const filteredItems = useMemo(() => {
    let filtered = items;
    if (search) {
      const q = search.toLowerCase();
      filtered = items.filter(i =>
        i.sku.toLowerCase().includes(q) || i.name.toLowerCase().includes(q)
      );
    }
    filtered = [...filtered].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      const numA = Number(aVal) || 0;
      const numB = Number(bVal) || 0;
      return sortDir === 'asc' ? numA - numB : numB - numA;
    });
    return filtered;
  }, [items, search, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const sortIndicator = (key: SortKey) => {
    if (sortKey !== key) return '';
    return sortDir === 'asc' ? ' \u2191' : ' \u2193';
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <div className="grid grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
      </div>
    );
  }

  if (!data) return <p className="text-brand-neutral/50">Inventory data unavailable</p>;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-8">
        <h1 className="font-display text-2xl font-bold text-brand-neutral">Current Stock</h1>
        <span className="text-xs text-brand-neutral/50">As of {data.as_of}</span>
      </div>

      {/* Summary */}
      <KpiGrid columns={4}>
        <KpiCard label="Total SKUs" value={fmtInt(counts.total)} />
        <KpiCard label="Critical (Red)" value={fmtInt(counts.red)} badges={counts.red > 0 ? [{ label: 'Needs attention', color: 'danger' }] : []} />
        <KpiCard label="Low (Yellow)" value={fmtInt(counts.yellow)} badges={counts.yellow > 0 ? [{ label: 'Monitor', color: 'warning' }] : []} />
        <KpiCard label="In Stock (OK)" value={fmtInt(counts.ok)} badges={[{ label: 'Healthy', color: 'success' }]} />
      </KpiGrid>

      {/* Order Tracking — Fulfillment Pipeline */}
      {data.order_tracking && (() => {
        const ot = data.order_tracking;
        const total = ot.total_30d ?? ot.total_orders ?? 0;
        const steps = [
          { label: 'Total Orders (30d)', value: total, color: 'bg-brand-neutral' },
          { label: 'Fulfilled', value: ot.fulfilled, color: 'bg-brand-primary' },
          { label: 'Backorders', value: ot.backorders, color: 'bg-ns-yellow' },
          { label: 'Not Fulfilled < 1 day', value: ot.unfulfilled_lt_1d ?? (ot.unfulfilled_by_age?.['< 1d'] ?? 0), color: 'bg-brand-secondary' },
          { label: 'Not Fulfilled < 5 days', value: ot.unfulfilled_lt_5d ?? (ot.unfulfilled_by_age?.['< 5d'] ?? 0), color: 'bg-brand-secondary/70' },
          { label: 'Not Fulfilled 5-10 days', value: ot.unfulfilled_5_to_10d ?? (ot.unfulfilled_by_age?.['5-10d'] ?? 0), color: 'bg-ns-yellow' },
          { label: 'Not Fulfilled > 10 days', value: ot.unfulfilled_gt_10d ?? (ot.unfulfilled_by_age?.['> 10d'] ?? 0), color: 'bg-ns-red' },
        ];
        return (
          <>
            <h2 className="font-display text-lg font-semibold text-brand-neutral mb-4">Order Tracking</h2>
            <div className="bg-surface-lowest rounded-xl shadow-ambient p-6 mb-8">
              <div className="flex items-stretch gap-1 overflow-x-auto">
                {steps.map((step, i) => (
                  <div key={step.label} className="flex items-stretch">
                    <div className="flex flex-col items-center justify-center px-4 py-3 min-w-[130px]">
                      <span className="text-[10px] uppercase tracking-wider text-brand-neutral/50 text-center mb-1.5 leading-tight">{step.label}</span>
                      <span className="text-2xl font-semibold text-brand-neutral">{fmtInt(step.value)}</span>
                      {total > 0 && i > 0 && (
                        <span className="text-[10px] text-brand-neutral/40 mt-0.5">
                          {((step.value / total) * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                    {i < steps.length - 1 && (
                      <div className="flex items-center px-1 text-brand-neutral/20 text-lg select-none">&rarr;</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </>
        );
      })()}

      {/* Search */}
      <div className="mb-5 max-w-xs">
        <input
          type="text"
          placeholder="Search SKU or product name..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full px-4 py-2.5 text-sm bg-surface-lowest rounded-xl shadow-ambient outline-none focus:ring-2 focus:ring-brand-primary/20 text-brand-neutral placeholder:text-brand-neutral/40"
        />
      </div>

      {/* Inventory Table */}
      <div className="bg-surface-lowest rounded-xl shadow-ambient overflow-x-auto">
        <table className="w-full text-sm border-collapse min-w-[800px]">
          <thead>
            <tr className="bg-surface-low">
              {[
                { key: 'sku' as SortKey, label: 'SKU' },
                { key: 'name' as SortKey, label: 'Product' },
                { key: 'qty' as SortKey, label: 'Qty' },
                { key: 'daily_velocity' as SortKey, label: 'Daily Vel.' },
                { key: 'days_remaining' as SortKey, label: 'Days Left' },
                { key: 'status' as SortKey, label: 'Status' },
              ].map(col => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold cursor-pointer hover:bg-brand-primary/5 select-none text-left transition-colors"
                >
                  {col.label}{sortIndicator(col.key)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredItems.map(item => (
              <tr key={item.sku} className={`hover:bg-surface-low transition-colors ${
                item.status === 'red' ? 'border-l-3 border-l-ns-red' : ''
              }`}>
                <td className="px-5 py-2.5 font-mono text-xs">{item.sku}</td>
                <td className="px-5 py-2.5">{item.name}</td>
                <td className="px-5 py-2.5 text-right">{fmtInt(item.qty)}</td>
                <td className="px-5 py-2.5 text-right">{item.daily_velocity.toFixed(1)}</td>
                <td className="px-5 py-2.5 text-right">{item.days_remaining >= 9999 ? '999+' : fmtInt(item.days_remaining)}</td>
                <td className="px-5 py-2.5">
                  <Chip
                    size="sm"
                    variant="soft"
                    color={item.status === 'red' ? 'danger' : item.status === 'yellow' ? 'warning' : 'success'}
                  >
                    {item.status === 'red' ? 'Critical' : item.status === 'yellow' ? 'Low' : 'OK'}
                  </Chip>
                </td>
              </tr>
            ))}
            {filteredItems.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-8 text-center text-brand-neutral/50">No matching items</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
