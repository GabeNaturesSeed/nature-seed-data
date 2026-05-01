'use client';

import { PnlMonth, PnlYtd } from '@/lib/types';
import { fmt, monthLabel } from '@/lib/formatters';

interface CmWaterfallTableProps {
  months: PnlMonth[];
  ytd: PnlYtd;
}

type Line = {
  label: string;
  compute: (m: Partial<PnlMonth>) => number | null;
  bold?: boolean;
  highlight?: boolean;
  subtract?: boolean;
  section?: boolean;
  showPct?: boolean;
};

const revenue = (m: Partial<PnlMonth>) => (m.seed_revenue ?? 0) + (m.revenue_freight ?? 0) + (m.discounts ?? 0);
const seedCogs = (m: Partial<PnlMonth>) => m.seed_cogs ?? 0;
const cm1 = (m: Partial<PnlMonth>) => revenue(m) - seedCogs(m);
const freightCost = (m: Partial<PnlMonth>) => m.cogs_freight ?? 0;
const marketingCost = (m: Partial<PnlMonth>) => (m.advertising ?? 0) + (m.development ?? 0);
const cm2 = (m: Partial<PnlMonth>) => cm1(m) - freightCost(m) - marketingCost(m);
const ga = (m: Partial<PnlMonth>) => m.total_ga ?? 0;
const netIncome = (m: Partial<PnlMonth>) => cm2(m) - ga(m);

const lines: Line[] = [
  { label: 'Revenue (Seed + Freight, net of discounts)', compute: revenue, bold: true },
  { label: 'Less: Seed COGS', compute: seedCogs, subtract: true },
  { label: 'CM1 (Gross contribution after seed COGS)', compute: cm1, bold: true, highlight: true, section: true, showPct: true },
  { label: 'Less: Freight Cost', compute: freightCost, subtract: true },
  { label: 'Less: Marketing Cost (Advertising + Development)', compute: marketingCost, subtract: true },
  { label: 'CM2 (Contribution after variable overhead)', compute: cm2, bold: true, highlight: true, section: true, showPct: true },
  { label: 'Less: OPEX (G&A)', compute: ga, subtract: true },
  { label: 'Net Income (after G&A only)', compute: netIncome, bold: true, highlight: true, section: true, showPct: true },
];

function fmtCell(val: number | null, subtract: boolean): string {
  if (val == null) return '\u2014';
  const abs = Math.abs(val);
  const formatted = fmt(abs);
  return subtract ? '(' + formatted + ')' : fmt(val);
}

function pctOfRevenue(val: number | null, rev: number): string | null {
  if (val == null || rev === 0) return null;
  return (val / rev * 100).toFixed(1) + '%';
}

export default function CmWaterfallTable({ months, ytd }: CmWaterfallTableProps) {
  return (
    <div className="bg-surface-lowest rounded-xl shadow-ambient overflow-x-auto">
      <table className="w-full text-sm border-collapse min-w-[700px]">
        <thead>
          <tr className="bg-surface-low">
            <th className="text-left px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold w-[26rem]">Line Item</th>
            {months.map(m => (
              <th key={m.month} className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">
                {monthLabel(m.month)}
                {m.source === 'budget' && <span className="block text-[10px] text-ns-yellow font-normal">(partial)</span>}
              </th>
            ))}
            <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">YTD</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, i) => (
            <tr
              key={i}
              className={`hover:bg-surface-low transition-colors ${line.highlight ? 'bg-brand-primary/5' : ''} ${line.section ? 'border-t border-brand-neutral/10' : ''}`}
            >
              <td className={`px-5 py-2.5 ${line.subtract ? 'pl-9 text-brand-neutral/70' : ''} ${line.bold ? 'font-semibold' : ''}`}>
                {line.label}
              </td>
              {months.map(m => {
                const val = line.compute(m as Partial<PnlMonth>);
                const rev = revenue(m as Partial<PnlMonth>);
                const pct = line.showPct ? pctOfRevenue(val, rev) : null;
                return (
                  <td
                    key={m.month}
                    className={`px-5 py-2.5 text-right ${line.bold ? 'font-semibold' : ''} ${val != null && val < 0 ? 'text-ns-red' : ''}`}
                  >
                    {fmtCell(val, !!line.subtract)}
                    {pct && <div className="text-[10px] text-brand-neutral/40 font-normal">{pct}</div>}
                  </td>
                );
              })}
              <td className={`px-5 py-2.5 text-right font-semibold ${line.bold ? '' : 'text-brand-neutral/80'}`}>
                {(() => {
                  const val = line.compute(ytd as Partial<PnlMonth>);
                  const rev = revenue(ytd as Partial<PnlMonth>);
                  const pct = line.showPct ? pctOfRevenue(val, rev) : null;
                  return <>
                    {fmtCell(val, !!line.subtract)}
                    {pct && <div className="text-[10px] text-brand-neutral/40 font-normal">{pct}</div>}
                  </>;
                })()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
