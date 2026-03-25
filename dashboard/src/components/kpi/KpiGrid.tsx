'use client';

import type { ReactNode } from 'react';

interface KpiGridProps {
  children: ReactNode;
  columns?: number;
}

export default function KpiGrid({ children, columns = 4 }: KpiGridProps) {
  const colClass = columns === 3
    ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'
    : columns === 5
    ? 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-5'
    : 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4';

  return (
    <div className={`grid ${colClass} gap-6 mb-8`}>
      {children}
    </div>
  );
}
