'use client';

import { Menu } from 'lucide-react';

interface MobileHeaderProps {
  onMenuToggle: () => void;
}

export default function MobileHeader({ onMenuToggle }: MobileHeaderProps) {
  return (
    <header className="md:hidden sticky top-0 z-40 h-14 flex items-center justify-between px-4 bg-surface-lowest shadow-ambient">
      <button
        onClick={onMenuToggle}
        className="p-2 -ml-2 rounded-lg hover:bg-surface-low transition-colors"
        aria-label="Open menu"
      >
        <Menu size={22} className="text-brand-neutral" />
      </button>
      <div className="flex items-center gap-2">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2d6A4F" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M7 20h10"/>
          <path d="M10 20c5.5-2.5.8-6.4 3-10"/>
          <path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z"/>
          <path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z"/>
        </svg>
        <span className="font-semibold text-sm text-brand-neutral">Nature&apos;s Seed</span>
      </div>
      {/* Spacer to balance the hamburger on the left */}
      <div className="w-10" />
    </header>
  );
}
