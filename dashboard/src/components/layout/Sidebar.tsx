'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  Calendar,
  ShoppingBag,
  Package,
  Megaphone,
  TrendingUp,
  FileText,
  StickyNote,
  DollarSign,
  ShoppingCart,
  Store,
  Boxes,
  LineChart,
  Warehouse,
  Truck,
  HeartPulse,
  ChevronDown,
  ChevronRight,
  X,
  type LucideIcon,
} from 'lucide-react';

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  children?: { label: string; href: string; icon: LucideIcon }[];
}

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

const navItems: NavItem[] = [
  {
    label: 'Reporting',
    href: '/reporting',
    icon: BarChart3,
    children: [
      { label: 'MTD Overview', href: '/reporting', icon: TrendingUp },
      { label: 'YTD Summary', href: '/reporting/ytd', icon: LineChart },
      { label: 'P&L Statement', href: '/reporting/pnl', icon: DollarSign },
      { label: 'Notes', href: '/reporting/notes', icon: StickyNote },
    ],
  },
  { label: 'Content Calendar', href: '/calendar', icon: Calendar },
  {
    label: 'Marketplaces',
    href: '/marketplaces/amazon',
    icon: ShoppingBag,
    children: [
      { label: 'Amazon', href: '/marketplaces/amazon', icon: ShoppingCart },
      { label: 'Walmart', href: '/marketplaces/walmart', icon: Store },
    ],
  },
  {
    label: 'Inventory',
    href: '/inventory',
    icon: Package,
    children: [
      { label: 'Current Stock', href: '/inventory', icon: Boxes },
      { label: 'Forecasting', href: '/inventory/forecasting', icon: LineChart },
      { label: 'FBA Inventory', href: '/inventory/fba', icon: Warehouse },
      { label: 'Shipping Insights', href: '/inventory/shipping', icon: Truck },
    ],
  },
  {
    label: 'Marketing',
    href: '/marketing',
    icon: Megaphone,
    children: [
      { label: 'Channel Performance', href: '/marketing', icon: TrendingUp },
      { label: 'Website Health', href: '/website-health', icon: HeartPulse },
    ],
  },
];

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const pathname = usePathname();

  function isChildActive(href: string): boolean {
    return pathname === href;
  }

  function isSectionActive(item: NavItem): boolean {
    if (item.children) {
      if (item.children.some(child => pathname === child.href || pathname.startsWith(child.href + '/'))) {
        return true;
      }
      const basePath = item.href.split('/').slice(0, 2).join('/');
      return pathname.startsWith(basePath);
    }
    return pathname === item.href;
  }

  const handleNavClick = () => {
    // Close sidebar on mobile when a nav item is clicked
    onClose?.();
  };

  const sidebarContent = (
    <aside className="w-60 min-h-screen bg-surface-low flex-shrink-0 flex flex-col">
      {/* Logo header */}
      <div className="h-16 flex items-center gap-3 px-5"
        style={{ background: 'linear-gradient(135deg, #2d6A4F 0%, #52796F 100%)' }}
      >
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M7 20h10"/>
          <path d="M10 20c5.5-2.5.8-6.4 3-10"/>
          <path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z"/>
          <path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z"/>
        </svg>
        <div className="flex-1">
          <div className="text-white font-semibold text-sm leading-tight">Nature&apos;s Seed</div>
          <div className="text-green-200 text-[10px] tracking-wider uppercase">Operations</div>
        </div>
        {/* Close button - only visible on mobile */}
        <button
          onClick={onClose}
          className="md:hidden p-1 rounded-lg hover:bg-white/20 transition-colors"
          aria-label="Close menu"
        >
          <X size={20} className="text-white" />
        </button>
      </div>

      <nav className="flex-1 py-4 overflow-y-auto">
        {navItems.map((item) => {
          const sectionActive = isSectionActive(item);
          const Icon = item.icon;
          const hasChildren = !!item.children;

          return (
            <div key={item.label} className="mb-1">
              <Link
                href={hasChildren ? item.children![0].href : item.href}
                onClick={handleNavClick}
                className={`flex items-center gap-3 mx-3 px-3 py-2.5 text-[13px] font-medium transition-all duration-150 rounded-xl ${
                  sectionActive
                    ? 'text-brand-primary bg-brand-primary/8'
                    : 'text-brand-neutral/60 hover:text-brand-neutral hover:bg-brand-primary/4'
                }`}
              >
                <Icon size={18} className={sectionActive ? 'text-brand-primary' : 'text-brand-tertiary/60'} />
                <span className="flex-1">{item.label}</span>
                {hasChildren && (
                  sectionActive
                    ? <ChevronDown size={14} className="text-brand-tertiary" />
                    : <ChevronRight size={14} className="text-brand-outline" />
                )}
              </Link>

              {hasChildren && sectionActive && (
                <div className="ml-9 mt-1 mb-1 pl-3"
                  style={{ borderLeft: '2px solid rgba(191, 201, 193, 0.3)' }}
                >
                  {item.children!.map((child) => {
                    const ChildIcon = child.icon;
                    const childActive = isChildActive(child.href);
                    return (
                      <Link
                        key={child.href}
                        href={child.href}
                        onClick={handleNavClick}
                        className={`flex items-center gap-2.5 px-3 py-1.5 text-xs transition-all duration-150 rounded-lg ${
                          childActive
                            ? 'text-brand-primary font-semibold bg-brand-primary/6'
                            : 'text-brand-neutral/50 hover:text-brand-neutral/80 hover:bg-brand-primary/4'
                        }`}
                      >
                        <ChildIcon size={14} className={childActive ? 'text-brand-primary' : 'text-brand-tertiary/40'} />
                        {child.label}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      <div className="px-5 py-3 text-[10px] text-brand-neutral/40">
        <div className="flex items-center gap-1.5">
          <FileText size={12} />
          <span>Dashboard v2.0</span>
        </div>
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop sidebar - always visible */}
      <div className="hidden md:block">
        {sidebarContent}
      </div>

      {/* Mobile sidebar - overlay */}
      <div className="md:hidden">
        {/* Backdrop */}
        {isOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/50 transition-opacity"
            onClick={onClose}
            aria-hidden="true"
          />
        )}

        {/* Slide-in sidebar */}
        <div
          className={`fixed inset-y-0 left-0 z-50 transform transition-transform duration-300 ease-in-out ${
            isOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          {sidebarContent}
        </div>
      </div>
    </>
  );
}
