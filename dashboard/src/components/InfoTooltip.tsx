'use client';

import { Tooltip } from '@heroui/react';
import { Info } from 'lucide-react';
import type { ReactNode } from 'react';

interface InfoTooltipProps {
  content: ReactNode;
  size?: number;
  className?: string;
}

export default function InfoTooltip({ content, size = 13, className = '' }: InfoTooltipProps) {
  return (
    <Tooltip delay={100} closeDelay={0}>
      <Tooltip.Trigger
        className={`inline-flex items-center justify-center text-brand-neutral/40 hover:text-brand-primary cursor-help align-middle ${className}`}
        aria-label="More info"
      >
        <Info size={size} strokeWidth={2} />
      </Tooltip.Trigger>
      <Tooltip.Content className="max-w-xs text-xs leading-snug bg-brand-neutral text-white rounded-md px-3 py-2 shadow-lg z-50">
        {content}
      </Tooltip.Content>
    </Tooltip>
  );
}
