'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { ReportingData, BudgetData } from '@/lib/types';
import { fmt, pct, calcPct, badgeColor, trendRunRate, monthLabel, cumulative, safe } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import ChartCard from '@/components/charts/ChartCard';
import InfoTooltip from '@/components/InfoTooltip';
import { Skeleton } from '@heroui/react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const dollarFormatter = (v: number) => '$' + (v / 1000).toFixed(0) + 'K';

// Net Revenue, COGS (incl. outbound freight), Advertising — from 2025 P&L spreadsheet
// CM2 = Net Revenue − Total COGS − Advertising
const LY_2025: Record<string, { revenue: number; cm2: number }> = {
  '2025-01': { revenue: 110988, cm2: -3878 },
  '2025-02': { revenue: 219218, cm2: 51305 },
  '2025-03': { revenue: 367345, cm2: 126050 },
  '2025-04': { revenue: 339121, cm2: 130362 },
  '2025-05': { revenue: 185877, cm2: 29649 },
  '2025-06': { revenue: 169436, cm2: 15969 },
  '2025-07': { revenue: 44121, cm2: 5826 },
  '2025-08': { revenue: 124842, cm2: 24974 },
  '2025-09': { revenue: 206811, cm2: 75219 },
  '2025-10': { revenue: 163739, cm2: 32161 },
  '2025-11': { revenue: 67404, cm2: 14406 },
  '2025-12': { revenue: 26645, cm2: -15645 },
};

export default function TrackingPage() {
  const { data, loading: loadingR } = useJsonData<ReportingData>('reporting');
  const { data: budget, loading: loadingB } = useJsonData<BudgetData>('budget');

  if (loadingR || loadingB) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      </div>
    );
  }

  if (!data) return <p className="text-brand-neutral/50">Tracking data unavailable</p>;

  const { mtd, ytd } = data;
  const cy = mtd.cy;
  const ly = mtd.ly;
  const mtdBudget = mtd.budget;
  const totCY = ytd.totals_cy;
  const totLY = ytd.totals_ly;
  const months = ytd.months;

  // ── Month context ─────────────────────────────────────────
  const firstDate = mtd.daily_cy.length
    ? new Date(mtd.daily_cy[0].date + 'T00:00:00')
    : new Date();
  const dim = new Date(firstDate.getFullYear(), firstDate.getMonth() + 1, 0).getDate();
  const daysElapsed = mtd.daily_cy.length;
  const currentMonth = `${firstDate.getFullYear()}-${String(firstDate.getMonth() + 1).padStart(2, '0')}`;

  // ── MTD Revenue ───────────────────────────────────────────
  const pacedBudgetRev = dim ? mtdBudget.revenue * daysElapsed / dim : 0;
  const mtdRevVsLY = calcPct(cy.revenue, ly.revenue);
  const mtdRevVsBudget = calcPct(cy.revenue, pacedBudgetRev);

  // ── YTD Revenue ───────────────────────────────────────────
  const ytdBudgetRev = budget
    ? months.reduce((s, m) => s + safe(budget.monthly[m.month]?.net_revenue), 0)
    : null;
  const ytdRevVsLY = calcPct(totCY.revenue, totLY.revenue);
  const ytdRevVsBudget = ytdBudgetRev ? calcPct(totCY.revenue, ytdBudgetRev) : null;

  // ── MTD Run Rate ──────────────────────────────────────────
  const runRate = trendRunRate(mtd.daily_cy);
  const mtdRunRateVal = runRate?.runRate ?? null;
  const lyMonthTotal = months.find(m => m.month === currentMonth)?.ly_revenue ?? null;
  const mtdRunRateVsLY = mtdRunRateVal && lyMonthTotal ? calcPct(mtdRunRateVal, lyMonthTotal) : null;
  const mtdRunRateVsBudget = mtdRunRateVal ? calcPct(mtdRunRateVal, mtdBudget.revenue) : null;

  // ── YTD Run Rate (annualized) ─────────────────────────────
  const isLeap = firstDate.getFullYear() % 4 === 0;
  const daysInYear = isLeap ? 366 : 365;
  const startOfYear = new Date(firstDate.getFullYear(), 0, 1);
  const todayDate = new Date(firstDate.getFullYear(), firstDate.getMonth(), daysElapsed);
  const daysElapsedInYear = Math.round((todayDate.getTime() - startOfYear.getTime()) / 86400000) + 1;
  const ytdRunRateVal = totCY.revenue && daysElapsedInYear
    ? totCY.revenue / daysElapsedInYear * daysInYear
    : null;
  const lyYtdRunRate = totLY.revenue && daysElapsedInYear
    ? totLY.revenue / daysElapsedInYear * daysInYear
    : null;
  const annualBudget = budget
    ? Object.values(budget.monthly).reduce((s, m) => s + safe(m.net_revenue), 0)
    : null;
  const ytdRunRateVsLY = ytdRunRateVal && lyYtdRunRate ? calcPct(ytdRunRateVal, lyYtdRunRate) : null;
  const ytdRunRateVsBudget = ytdRunRateVal && annualBudget ? calcPct(ytdRunRateVal, annualBudget) : null;

  // ── MTD Margin (CM2 = Rev − COGS − Freight − Ads) ────────
  const mtdMargin = cy.cm2 ?? null;
  const mtdCm2Pct = cy.cm2_pct ?? null;
  const mtdBudgetMonth = budget?.monthly[currentMonth];
  const mtdBudgetMarginPaced = mtdBudgetMonth && dim
    ? (safe(mtdBudgetMonth.gross_margin) - safe(mtdBudgetMonth.ad_spend)) * daysElapsed / dim
    : null;
  const mtdMarginVsBudget = mtdMargin != null && mtdBudgetMarginPaced
    ? calcPct(mtdMargin, mtdBudgetMarginPaced)
    : null;

  // ── YTD Margin (CM2) ──────────────────────────────────────
  const ytdMargin = totCY.cm2 ?? null;
  const ytdCm2Pct = totCY.cm2_pct ?? null;
  const ytdBudgetMargin = budget
    ? months.reduce((s, m) => {
        const bm = budget.monthly[m.month];
        return s + (bm ? safe(bm.gross_margin) - safe(bm.ad_spend) : 0);
      }, 0)
    : null;
  const ytdMarginVsBudget = ytdMargin != null && ytdBudgetMargin
    ? calcPct(ytdMargin, ytdBudgetMargin)
    : null;

  // ── LY 2025 Margin (hardcoded from 2025 P&L spreadsheet) ─────────────────
  const lyMonthKey = `2025-${currentMonth.slice(5)}`;
  const lyMonthData = LY_2025[lyMonthKey];
  const mtdLyCm2Paced = lyMonthData && dim ? lyMonthData.cm2 * daysElapsed / dim : null;
  const mtdMarginVsLY = mtdMargin != null && mtdLyCm2Paced != null
    ? calcPct(mtdMargin, mtdLyCm2Paced)
    : null;

  const ytdLyCm2 = months.reduce((sum, m, i) => {
    const lyKey = `2025-${m.month.slice(5)}`;
    const lyData = LY_2025[lyKey];
    if (!lyData) return sum;
    const isLast = i === months.length - 1;
    const monthCm2 = isLast && dim ? lyData.cm2 * daysElapsed / dim : lyData.cm2;
    return sum + monthCm2;
  }, 0);
  const ytdMarginVsLY = ytdMargin != null ? calcPct(ytdMargin, ytdLyCm2) : null;

  // ── Revenue chart data (cumulative monthly) ───────────────
  const cyCumRev = cumulative(months.map(m => safe(m.revenue)));
  const lyCumRev = cumulative(months.map(m => safe(m.ly_revenue)));
  const budCumRev = budget
    ? cumulative(months.map(m => safe(budget.monthly[m.month]?.net_revenue)))
    : [];

  const revenueChartData = months.map((m, i) => ({
    name: monthLabel(m.month),
    cy: cyCumRev[i],
    ly: lyCumRev[i],
    budget: budCumRev[i] ?? null,
  }));

  // ── Margin chart data (monthly CM2 bars) ─────────────────
  const marginChartData = months.map(m => {
    const bm = budget?.monthly[m.month];
    const lyKey = `2025-${m.month.slice(5)}`;
    return {
      name: monthLabel(m.month),
      cy: safe(m.cm2),
      ly: LY_2025[lyKey]?.cm2 ?? null,
      budget: bm ? safe(bm.gross_margin) - safe(bm.ad_spend) : null,
    };
  });

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">CFO Tracking</h1>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">As of {data.as_of}</span>
      </div>

      {/* 6 widgets — 2 columns × 3 rows */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 mb-8">

        {/* ── MTD Revenue ── */}
        <KpiCard
          label="MTD Revenue"
          value={fmt(cy.revenue)}
          tooltip="Month-to-date WooCommerce revenue vs same period last year and prorated monthly budget."
          badges={[
            { label: `vs LY ${pct(mtdRevVsLY)}`, color: badgeColor(mtdRevVsLY) },
            { label: `vs Budget Pace ${pct(mtdRevVsBudget)}`, color: badgeColor(mtdRevVsBudget) },
          ]}
        />

        {/* ── YTD Revenue ── */}
        <KpiCard
          label="YTD Revenue"
          value={fmt(totCY.revenue)}
          tooltip="Year-to-date WooCommerce revenue vs same YTD period last year and cumulative budget."
          badges={[
            { label: `vs LY ${pct(ytdRevVsLY)}`, color: badgeColor(ytdRevVsLY) },
            ...(ytdRevVsBudget != null
              ? [{ label: `vs Budget ${pct(ytdRevVsBudget)}`, color: badgeColor(ytdRevVsBudget) }]
              : []),
          ]}
        />

        {/* ── MTD Run Rate ── */}
        <KpiCard
          label="MTD Run Rate"
          value={fmt(mtdRunRateVal)}
          tooltip="Trend-adjusted month-end projection. OLS regression on daily revenue — blends full-month slope with recent 7-day slope, weighted by R². Accounts for acceleration and deceleration."
          badges={[
            ...(mtdRunRateVsLY != null
              ? [{ label: `vs LY Full Month ${pct(mtdRunRateVsLY)}`, color: badgeColor(mtdRunRateVsLY) }]
              : []),
            ...(mtdRunRateVsBudget != null
              ? [{ label: `vs Month Budget ${pct(mtdRunRateVsBudget)}`, color: badgeColor(mtdRunRateVsBudget) }]
              : []),
          ]}
          note={runRate ? `Trend-adjusted · R² ${(runRate.trendR2 * 100).toFixed(0)}% · avg ${fmt(runRate.avgDaily)}/day` : undefined}
        />

        {/* ── YTD Run Rate ── */}
        <KpiCard
          label="YTD Run Rate (Annualized)"
          value={fmt(ytdRunRateVal)}
          tooltip={`Full-year revenue projection based on YTD daily pace (${daysElapsedInYear} of ${daysInYear} days elapsed).`}
          badges={[
            ...(ytdRunRateVsLY != null
              ? [{ label: `vs LY Run Rate ${pct(ytdRunRateVsLY)}`, color: badgeColor(ytdRunRateVsLY) }]
              : []),
            ...(ytdRunRateVsBudget != null
              ? [{ label: `vs Annual Budget ${pct(ytdRunRateVsBudget)}`, color: badgeColor(ytdRunRateVsBudget) }]
              : []),
          ]}
          note={`${daysElapsedInYear} of ${daysInYear} days · ${fmt(annualBudget)} annual budget`}
        />

        {/* ── MTD Margin ── */}
        <KpiCard
          label="MTD CM2 Margin"
          value={fmt(mtdMargin)}
          tooltip="Contribution Margin 2 = Revenue − COGS − Shipping/Freight − Ad Spend. Budget est. = gross margin − ad spend (freight excluded from budget data). LY not available at this granularity."
          badges={[
            ...(mtdMarginVsLY != null
              ? [{ label: `vs LY ${pct(mtdMarginVsLY)}`, color: badgeColor(mtdMarginVsLY) }]
              : []),
            ...(mtdMarginVsBudget != null
              ? [{ label: `vs Budget Est. ${pct(mtdMarginVsBudget)}`, color: badgeColor(mtdMarginVsBudget) }]
              : []),
          ]}
          note={mtdCm2Pct != null ? `${mtdCm2Pct.toFixed(1)}% CM2 · Rev − COGS − Freight − Ads` : undefined}
        />

        {/* ── YTD Margin ── */}
        <KpiCard
          label="YTD CM2 Margin"
          value={fmt(ytdMargin)}
          tooltip="YTD Contribution Margin 2. Budget = sum of (gross_margin − ad_spend) for elapsed months — freight excluded from budget data. LY cost breakdown not available."
          badges={[
            ...(ytdMarginVsLY != null
              ? [{ label: `vs LY ${pct(ytdMarginVsLY)}`, color: badgeColor(ytdMarginVsLY) }]
              : []),
            ...(ytdMarginVsBudget != null
              ? [{ label: `vs Budget Est. ${pct(ytdMarginVsBudget)}`, color: badgeColor(ytdMarginVsBudget) }]
              : []),
          ]}
          note={ytdCm2Pct != null ? `${ytdCm2Pct.toFixed(1)}% CM2 · Rev − COGS − Freight − Ads` : undefined}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard
          title="Cumulative YTD Revenue"
          tooltip="Monthly cumulative revenue — current year vs last year vs budget."
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={revenueChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#212529' }} />
              <YAxis tickFormatter={dollarFormatter} tick={{ fontSize: 10, fill: '#212529' }} />
              <Tooltip formatter={(v) => fmt(Number(v))} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="cy" name="CY Revenue" stroke="#2d6A4F" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="ly" name="LY Revenue" stroke="#52796F" strokeWidth={1.5} strokeDasharray="5 4" dot={{ r: 2 }} />
              <Line type="monotone" dataKey="budget" name="Budget" stroke="#888" strokeWidth={1.5} strokeDasharray="2 3" dot={{ r: 2 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Monthly CM2 Margin"
          tooltip="Contribution Margin 2 per month (Rev − COGS − Freight − Ads) vs budget estimate (gross margin − ad spend, freight excluded from budget data)."
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={marginChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#212529' }} />
              <YAxis tickFormatter={dollarFormatter} tick={{ fontSize: 10, fill: '#212529' }} />
              <Tooltip formatter={(v) => fmt(Number(v))} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="cy" name="CY CM2" fill="#2d6a4f" radius={[3, 3, 0, 0]} />
              <Bar dataKey="ly" name="LY CM2" fill="#8bb4a0" radius={[3, 3, 0, 0]} opacity={0.7} />
              <Bar dataKey="budget" name="Budget CM2 (est.)" fill="#52796F" radius={[3, 3, 0, 0]} opacity={0.6} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}
