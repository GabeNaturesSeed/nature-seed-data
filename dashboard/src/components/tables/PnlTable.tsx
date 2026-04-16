'use client';

import { PnlMonth, PnlYtd } from '@/lib/types';
import { fmt, monthLabel } from '@/lib/formatters';

interface PnlTableProps {
  months: PnlMonth[];
  ytd: PnlYtd;
}

type RowDef = {
  label: string;
  key?: string;
  budgetKey?: string;
  bold?: boolean;
  indent?: boolean;
  separator?: boolean;
  highlight?: boolean;
};

const rows: RowDef[] = [
  { label: 'REVENUE', separator: true },
  { label: 'Seed Revenue', key: 'seed_revenue' },
  { label: 'Freight Revenue', key: 'revenue_freight' },
  { label: 'Discounts & Allowances', key: 'discounts' },
  { label: 'Net Revenue', key: 'revenue', budgetKey: 'budget_revenue', bold: true },
  { label: '', separator: true },
  { label: 'COST OF GOODS SOLD', separator: true },
  { label: 'Seed COGS', key: 'seed_cogs' },
  { label: 'Freight COGS', key: 'cogs_freight' },
  { label: 'Total COGS', key: 'cogs', budgetKey: 'budget_cogs', bold: true },
  { label: '', separator: true },
  { label: 'Gross Profit', key: 'gross_profit', budgetKey: 'budget_gross_profit', bold: true, highlight: true },
  { label: 'Gross Margin %', key: 'gross_margin_pct' },
  { label: '', separator: true },
  { label: 'OPERATING EXPENSES', separator: true },
  { label: 'Production / Warehouse', key: 'production_warehouse', indent: true },
  { label: 'Advertising', key: 'advertising', budgetKey: 'budget_advertising', indent: true },
  { label: 'Marketing', key: 'marketing', indent: true },
  { label: 'Development', key: 'development', indent: true },
  { label: 'Total S&M&A', key: 'total_sma', bold: true },
  { label: 'G&A Salaries', key: 'ga_salaries', indent: true },
  { label: 'Professional Fees', key: 'professional_fees', indent: true },
  { label: 'Insurance', key: 'insurance', indent: true },
  { label: 'Travel & Ent.', key: 'travel_entertainment', indent: true },
  { label: 'Utilities & Supplies', key: 'utilities_supplies', indent: true },
  { label: 'Corporate Allocation', key: 'corporate_allocation', indent: true },
  { label: 'G&A Other', key: 'ga_other', indent: true },
  { label: 'Total G&A', key: 'total_ga', bold: true },
  { label: 'Total OPEX', key: 'total_opex', budgetKey: 'budget_opex', bold: true },
  { label: '', separator: true },
  { label: 'Net Income', key: 'net_income', budgetKey: 'budget_net_income', bold: true, highlight: true },
  { label: 'Depreciation', key: 'depreciation', indent: true },
  { label: 'EBITDA', key: 'ebitda', budgetKey: 'budget_ebitda', bold: true, highlight: true },
];

function getVal(obj: Record<string, unknown>, key: string): number | null {
  const v = obj[key];
  if (v == null || typeof v !== 'number') return null;
  return v;
}

function fmtCell(val: number | null, isPercent: boolean = false): string {
  if (val == null) return '\u2014';
  if (isPercent) return val.toFixed(1) + '%';
  return fmt(val);
}

// For cost lines, lower actual is favorable (positive variance = bad)
const costKeys = new Set(['cogs', 'advertising', 'total_opex']);

function isFavorable(key: string | undefined, variance: number): boolean {
  if (!key) return variance >= 0;
  // Revenue / profit lines: positive variance = good
  // Cost lines: negative variance = good (spent less than budget)
  if (costKeys.has(key)) return variance <= 0;
  return variance >= 0;
}

function fmtVariance(val: number): string {
  const sign = val >= 0 ? '+' : '';
  return sign + fmt(val);
}

function fmtPctVar(actual: number, budget: number): string {
  if (budget === 0) return '\u2014';
  const pctVar = ((actual - budget) / Math.abs(budget)) * 100;
  return (pctVar >= 0 ? '+' : '') + pctVar.toFixed(1) + '%';
}

export default function PnlTable({ months, ytd }: PnlTableProps) {
  return (
    <div className="bg-surface-lowest rounded-xl shadow-ambient overflow-x-auto">
      <table className="w-full text-sm border-collapse min-w-[700px]">
        <thead>
          <tr className="bg-surface-low">
            <th className="text-left px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold w-48">Line Item</th>
            {months.map(m => (
              <th key={m.month} className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">
                {monthLabel(m.month)}
                {m.source === 'budget' && <span className="block text-[10px] text-ns-yellow font-normal">(partial)</span>}
              </th>
            ))}
            <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">YTD Actual</th>
            <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">YTD Budget</th>
            <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">Variance</th>
            <th className="text-right px-5 py-3.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold">% Var</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            if (row.separator && !row.label) {
              return <tr key={i}><td colSpan={months.length + 5} className="h-2"></td></tr>;
            }
            if (row.separator) {
              return (
                <tr key={i} className="bg-surface-low">
                  <td colSpan={months.length + 5} className="px-5 py-2.5 text-xs uppercase tracking-wider text-brand-neutral/50 font-bold">
                    {row.label}
                  </td>
                </tr>
              );
            }
            const isPercent = row.key === 'gross_margin_pct';
            return (
              <tr key={i} className={`hover:bg-surface-low transition-colors ${row.highlight ? 'bg-brand-primary/5' : ''}`}>
                <td className={`px-5 py-2.5 ${row.indent ? 'pl-9' : ''} ${row.bold ? 'font-semibold' : ''}`}>
                  {row.label}
                </td>
                {months.map(m => {
                  const mRec = m as unknown as Record<string, unknown>;
                  let cellTitle: string | undefined;
                  if (row.key === 'cogs_freight' && typeof m.source_freight_cogs === 'string') {
                    cellTitle = m.source_freight_cogs;
                    if (typeof m.shippo_freight === 'number' && m.source_freight_cogs.includes('%')) {
                      cellTitle += ` — Shippo quote: ${fmt(m.shippo_freight)}`;
                    }
                  } else if (row.key === 'revenue_freight' && typeof m.source_freight_revenue === 'string') {
                    cellTitle = m.source_freight_revenue;
                  } else if (row.key === 'seed_revenue' && typeof m.source_revenue === 'string') {
                    cellTitle = m.source_revenue;
                  } else if (row.key === 'seed_cogs' && typeof m.source_cogs === 'string') {
                    cellTitle = m.source_cogs;
                  }
                  const isEstimated = row.key === 'cogs_freight' && cellTitle?.startsWith('Estimated');
                  return (
                    <td
                      key={m.month}
                      title={cellTitle}
                      className={`px-5 py-2.5 text-right ${row.bold ? 'font-semibold' : ''} ${
                        row.key && getVal(mRec, row.key!) !== null && (getVal(mRec, row.key!) ?? 0) < 0 ? 'text-ns-red' : ''
                      } ${cellTitle ? 'cursor-help' : ''} ${isEstimated ? 'italic text-brand-neutral/70' : ''}`}
                    >
                      {row.key ? fmtCell(getVal(mRec, row.key), isPercent) : ''}
                    </td>
                  );
                })}
                <td className={`px-5 py-2.5 text-right font-semibold ${
                  row.key && getVal(ytd as unknown as Record<string, unknown>, row.key!) !== null &&
                  (getVal(ytd as unknown as Record<string, unknown>, row.key!) ?? 0) < 0 ? 'text-ns-red' : ''
                }`}>
                  {row.key ? fmtCell(getVal(ytd as unknown as Record<string, unknown>, row.key), isPercent) : ''}
                </td>
                {/* Budget column */}
                <td className="px-5 py-2.5 text-right text-brand-neutral/70">
                  {row.budgetKey
                    ? fmtCell(getVal(ytd as unknown as Record<string, unknown>, row.budgetKey), isPercent)
                    : '\u2014'}
                </td>
                {/* Variance column */}
                {(() => {
                  if (!row.budgetKey || !row.key) return (
                    <>
                      <td className="px-5 py-2.5 text-right text-brand-neutral/50">{'\u2014'}</td>
                      <td className="px-5 py-2.5 text-right text-brand-neutral/50">{'\u2014'}</td>
                    </>
                  );
                  const actual = getVal(ytd as unknown as Record<string, unknown>, row.key);
                  const budget = getVal(ytd as unknown as Record<string, unknown>, row.budgetKey);
                  if (actual == null || budget == null) return (
                    <>
                      <td className="px-5 py-2.5 text-right text-brand-neutral/50">{'\u2014'}</td>
                      <td className="px-5 py-2.5 text-right text-brand-neutral/50">{'\u2014'}</td>
                    </>
                  );
                  const variance = actual - budget;
                  const favorable = isFavorable(row.key, variance);
                  const colorClass = variance === 0 ? '' : favorable ? 'text-ns-green-dark' : 'text-ns-red';
                  return (
                    <>
                      <td className={`px-5 py-2.5 text-right font-semibold ${colorClass}`}>
                        {fmtVariance(variance)}
                      </td>
                      <td className={`px-5 py-2.5 text-right font-semibold ${colorClass}`}>
                        {fmtPctVar(actual, budget)}
                      </td>
                    </>
                  );
                })()}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
