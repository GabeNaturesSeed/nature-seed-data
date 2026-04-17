'use client';

import type { ReactNode } from 'react';
import InfoTooltip from '@/components/InfoTooltip';

interface ChartCardProps {
  title: string;
  children: ReactNode;
  height?: number;
  tooltip?: ReactNode;
}

export default function ChartCard({ title, children, height = 280, tooltip }: ChartCardProps) {
  return (
    <div className="bg-surface-lowest rounded-xl shadow-ambient p-4 md:p-6">
      <h3 className="font-display text-base md:text-lg font-semibold text-brand-neutral mb-3 md:mb-5 flex items-center gap-1.5">
        <span>{title}</span>
        {tooltip && <InfoTooltip content={tooltip} size={14} />}
      </h3>
      <div style={{ height, minHeight: 200 }}>
        {children}
      </div>
    </div>
  );
}
