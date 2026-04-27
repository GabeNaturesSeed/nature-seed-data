'use client';

import { useState, useMemo } from 'react';
import { useJsonData } from '@/hooks/useJsonData';
import { AbcReportData, AbcItem } from '@/lib/types';
import { fmt, fmtInt, pctPlain } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import ChartCard from '@/components/charts/ChartCard';
import { Skeleton, Chip } from '@heroui/react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

type ClassFilter = 'All' | 'A' | 'B' | 'C';
type SortKey = keyof AbcItem;
type SortDir = 'asc' | 'desc';

const CLASS_COLORS: Record<string, string> = {
  A: '#2d6a4f',
  B: '#d4a373',
  C: '#c96a2e',
};

export default function AbcReportPage() {
  const { data, loading } = useJsonData<AbcReportData>('abc_report');

  const seasonKeys = useMemo(() => (data ? Object.keys(data.seasons) : []), [data]);
  const [selectedSeason, setSelectedSeason] = useState<string>('');
  const [classFilter, setClassFilter] = useState<ClassFilter>('All');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('revenue');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  // Set default season once data loads
  const activeSeason = selectedSeason || seasonKeys[0] || '';
  const season = data?.seasons[activeSeason];

  // Must be before any early returns — Rules of Hooks
  const filteredItems = useMemo(() => {
    if (!season) return [];
    let items = [...season.items];

    if (classFilter !== 'All') {
      items = items.filter(i => i.class === classFilter);
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      items = items.filter(i => i.sku.toLowerCase().includes(q) || i.name.toLowerCase().includes(q));
    }

    items.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === 'number' && typeof bv === 'number') {
        return sortDir === 'asc' ? av - bv : bv - av;
      }
      return sortDir === 'asc'
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });

    return items;
  }, [season, classFilter, search, sortKey, sortDir]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      </div>
    );
  }

  if (!data || !season) return <p className="text-brand-neutral/50">ABC report data unavailable</p>;

  const { summary } = season;

  // Chart data for stacked bar
  const stackedData = [
    { label: 'Revenue Distribution', A: summary.a_revenue, B: summary.b_revenue, C: summary.c_revenue },
  ];

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sortArrow = (key: SortKey) => {
    if (sortKey !== key) return '';
    return sortDir === 'asc' ? ' \u25B2' : ' \u25BC';
  };

  const classChip = (cls: string) => (
    <span
      className="inline-flex items-center justify-center rounded-full px-2.5 py-0.5 text-xs font-semibold text-white"
      style={{ backgroundColor: CLASS_COLORS[cls] || '#888' }}
    >
      {cls}
    </span>
  );

  const filterTabs: ClassFilter[] = ['All', 'A', 'B', 'C'];

  return (
    <div>
      {/* Header + Season Selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-baseline justify-between gap-3 mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">ABC Product Report</h1>
        <div className="flex items-center gap-3">
          <select
            value={activeSeason}
            onChange={e => setSelectedSeason(e.target.value)}
            className="text-sm bg-surface-lowest border border-brand-outline/20 rounded-lg px-3 py-1.5 text-brand-neutral focus:outline-none focus:ring-1 focus:ring-brand-primary"
          >
            {seasonKeys.map(k => (
              <option key={k} value={k}>{data.seasons[k].label}</option>
            ))}
          </select>
          <span className="text-[10px] md:text-xs text-brand-neutral/50">Generated {data.generated}</span>
        </div>
      </div>

      {/* Period subtitle */}
      <p className="text-sm text-brand-neutral/50 mb-4">{season.period}</p>

      {/* KPI Cards */}
      <KpiGrid columns={4}>
        <KpiCard
          label="A Products"
          value={fmtInt(summary.a_count)}
          note={`${fmt(summary.a_revenue)} (${pctPlain(summary.a_pct)} of rev)`}
        />
        <KpiCard
          label="B Products"
          value={fmtInt(summary.b_count)}
          note={`${fmt(summary.b_revenue)} (${pctPlain(summary.b_pct)} of rev)`}
        />
        <KpiCard
          label="C Products"
          value={fmtInt(summary.c_count)}
          note={`${fmt(summary.c_revenue)} (${pctPlain(summary.c_pct)} of rev)`}
        />
        <KpiCard
          label="Season Revenue"
          value={fmt(season.total_revenue)}
          note={`${fmtInt(season.total_orders)} orders across ${fmtInt(season.total_skus)} SKUs`}
        />
      </KpiGrid>

      {/* Stacked Bar */}
      <ChartCard title="A / B / C Revenue Distribution" height={80}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={stackedData} layout="vertical" barSize={36}>
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="label" hide />
            <Tooltip
              formatter={(v: unknown, name: unknown) => [fmt(Number(v) || 0), `Class ${String(name)}`]}
              contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 2px 8px rgba(0,0,0,0.12)' }}
            />
            <Bar dataKey="A" stackId="abc" fill={CLASS_COLORS.A} radius={[6, 0, 0, 6]} />
            <Bar dataKey="B" stackId="abc" fill={CLASS_COLORS.B} />
            <Bar dataKey="C" stackId="abc" fill={CLASS_COLORS.C} radius={[0, 6, 6, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Legend for stacked bar */}
      <div className="flex gap-6 mb-8 mt-2 text-xs text-brand-neutral/60">
        {(['A', 'B', 'C'] as const).map(cls => (
          <div key={cls} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: CLASS_COLORS[cls] }} />
            <span>Class {cls} — {fmt(summary[`${cls.toLowerCase()}_revenue` as keyof typeof summary] as number)} ({pctPlain(summary[`${cls.toLowerCase()}_pct` as keyof typeof summary] as number)})</span>
          </div>
        ))}
      </div>

      {/* Filter Tabs + Search */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-4">
        <div className="flex gap-2">
          {filterTabs.map(tab => (
            <button
              key={tab}
              onClick={() => setClassFilter(tab)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                classFilter === tab
                  ? 'bg-brand-primary text-white'
                  : 'bg-surface-low text-brand-neutral/60 hover:bg-brand-primary/10'
              }`}
            >
              {tab === 'All' ? 'All' : `${tab} Only`}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Search SKU or product name..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="text-sm bg-surface-lowest border border-brand-outline/20 rounded-lg px-3 py-1.5 w-full sm:w-64 text-brand-neutral placeholder:text-brand-neutral/40 focus:outline-none focus:ring-1 focus:ring-brand-primary"
        />
        <span className="text-xs text-brand-neutral/40 ml-auto">{fmtInt(filteredItems.length)} items</span>
      </div>

      {/* Data Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr style={{ background: '#2d6A4F' }}>
              {([
                ['class', 'Class'],
                ['sku', 'SKU'],
                ['name', 'Product'],
                ['revenue', 'Revenue'],
                ['margin', 'Margin'],
                ['margin_pct', 'Margin %'],
                ['units', 'Units'],
                ['orders', 'Orders'],
                ['avg_basket', 'Avg Basket'],
                ['daily_velocity', 'Velocity'],
                ['backorder_rate', 'BO %'],
                ['reason', 'Reason'],
              ] as [SortKey, string][]).map(([key, label], i, arr) => (
                <th
                  key={key}
                  onClick={() => handleSort(key)}
                  className={`text-white py-3 px-3 font-medium cursor-pointer select-none whitespace-nowrap ${
                    key === 'name' || key === 'reason' ? 'text-left' : 'text-right'
                  } ${i === 0 ? 'rounded-tl-xl text-left' : ''} ${i === arr.length - 1 ? 'rounded-tr-xl' : ''}`}
                >
                  {label}{sortArrow(key)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((item, i) => (
              <tr key={item.sku} className={i % 2 === 0 ? 'bg-surface-lowest' : 'bg-surface-low'}>
                <td className="py-2.5 px-3">{classChip(item.class)}</td>
                <td className="py-2.5 px-3 text-right font-mono text-xs">{item.sku}</td>
                <td className="py-2.5 px-3 text-left max-w-[200px] truncate" title={item.name}>{item.name}</td>
                <td className="py-2.5 px-3 text-right font-semibold">{fmt(item.revenue)}</td>
                <td className="py-2.5 px-3 text-right">{fmt(item.margin)}</td>
                <td className="py-2.5 px-3 text-right">{pctPlain(item.margin_pct)}</td>
                <td className="py-2.5 px-3 text-right">{fmtInt(item.units)}</td>
                <td className="py-2.5 px-3 text-right">{fmtInt(item.orders)}</td>
                <td className="py-2.5 px-3 text-right">{fmt(item.avg_basket)}</td>
                <td className="py-2.5 px-3 text-right">{item.daily_velocity.toFixed(1)}</td>
                <td className="py-2.5 px-3 text-right">{pctPlain(item.backorder_rate)}</td>
                <td className="py-2.5 px-3 text-left text-xs text-brand-neutral/60 max-w-[180px] truncate" title={item.reason}>{item.reason}</td>
              </tr>
            ))}
            {filteredItems.length === 0 && (
              <tr>
                <td colSpan={12} className="py-8 text-center text-brand-neutral/40">No products match your filters</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
