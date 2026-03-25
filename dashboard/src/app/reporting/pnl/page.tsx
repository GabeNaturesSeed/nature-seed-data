'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { ReportingData } from '@/lib/types';
import PnlTable from '@/components/tables/PnlTable';
import { Skeleton } from '@heroui/react';

export default function PnlPage() {
  const { data, loading } = useJsonData<ReportingData>('reporting');

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <Skeleton className="h-96 rounded-xl" />
      </div>
    );
  }

  if (!data) return <p className="text-brand-neutral/50">P&L data unavailable</p>;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-8">
        <h1 className="text-2xl font-display font-bold text-brand-neutral">P&L Statement</h1>
        <span className="text-xs text-brand-neutral/50">As of {data.as_of}</span>
      </div>

      <PnlTable months={data.pnl.months} ytd={data.pnl.ytd} />
    </div>
  );
}
