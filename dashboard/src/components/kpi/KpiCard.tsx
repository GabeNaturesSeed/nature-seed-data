'use client';

import { Chip } from '@heroui/react';
import type { ReactNode } from 'react';
import InfoTooltip from '@/components/InfoTooltip';

interface KpiBadge {
  label: string;
  color: 'success' | 'danger' | 'default' | 'warning' | 'accent';
}

interface KpiCardProps {
  label: string;
  value: string;
  badges?: KpiBadge[];
  note?: string;
  tooltip?: ReactNode;
}

export default function KpiCard({ label, value, badges, note, tooltip }: KpiCardProps) {
  return (
    <div className="bg-surface-lowest rounded-xl shadow-ambient p-4 md:p-5">
      <p className="text-[10px] md:text-xs uppercase tracking-wider text-brand-neutral/50 mb-1.5 md:mb-2 flex items-center gap-1.5">
        <span>{label}</span>
        {tooltip && <InfoTooltip content={tooltip} />}
      </p>
      <p className="text-2xl md:text-3xl font-semibold text-brand-neutral mb-2 md:mb-2.5 leading-none">{value}</p>
      <div className="flex flex-col gap-1">
        {badges?.map((b, i) => (
          <Chip key={i} size="sm" variant="soft" color={b.color} className="text-xs">
            {b.label}
          </Chip>
        ))}
        {note && (
          <span className="text-xs text-brand-neutral/50">{note}</span>
        )}
      </div>
    </div>
  );
}
