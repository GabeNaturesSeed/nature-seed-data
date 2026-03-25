'use client';

import type { ReactNode } from 'react';

interface ChartCardProps {
  title: string;
  children: ReactNode;
  height?: number;
}

export default function ChartCard({ title, children, height = 280 }: ChartCardProps) {
  return (
    <div className="bg-surface-lowest rounded-xl shadow-ambient p-4 md:p-6">
      <h3 className="font-display text-base md:text-lg font-semibold text-brand-neutral mb-3 md:mb-5">{title}</h3>
      <div style={{ height, minHeight: 200 }}>
        {children}
      </div>
    </div>
  );
}
