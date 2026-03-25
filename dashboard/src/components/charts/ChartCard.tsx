'use client';

import type { ReactNode } from 'react';

interface ChartCardProps {
  title: string;
  children: ReactNode;
  height?: number;
}

export default function ChartCard({ title, children, height = 280 }: ChartCardProps) {
  return (
    <div className="bg-surface-lowest rounded-xl shadow-ambient p-6">
      <h3 className="font-display text-lg font-semibold text-brand-neutral mb-5">{title}</h3>
      <div style={{ height }}>
        {children}
      </div>
    </div>
  );
}
