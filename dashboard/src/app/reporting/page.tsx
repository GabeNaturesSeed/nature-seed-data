'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { ReportingData, SeasonalityData } from '@/lib/types';
import { fmt, fmtInt, ratio, pct, calcPct, badgeColor, linearProjection, trendRunRate, cumulative, safe, shortDate } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import ChartCard from '@/components/charts/ChartCard';
import { sources } from '@/lib/sources';
import InfoTooltip from '@/components/InfoTooltip';
import { Skeleton, Accordion, AccordionItem, AccordionHeading, AccordionTrigger, AccordionPanel, AccordionBody } from '@heroui/react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  AreaChart, Area, ResponsiveContainer,
} from 'recharts';

const dollarFormatter = (v: number) => '$' + (v / 1000).toFixed(0) + 'K';

export default function ReportingMtdPage() {
  const { data, loading } = useJsonData<ReportingData>('reporting');
  const { data: seasonality } = useJsonData<SeasonalityData>('seasonality');

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48 rounded-xl" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      </div>
    );
  }

  if (!data) return <p className="text-brand-neutral/50">Reporting data unavailable</p>;

  const { mtd } = data;
  const cy = mtd.cy;
  const ly = mtd.ly;
  const budget = mtd.budget;

  // Prorate monthly budget to MTD pace so "vs Budget" compares apples-to-apples
  // (days elapsed vs full month). Without this, early-month MTD looks artificially
  // far behind a whole-month target.
  const mtdFirstDate = mtd.daily_cy.length ? new Date(mtd.daily_cy[0].date + 'T00:00:00') : new Date();
  const daysInMonth = new Date(mtdFirstDate.getFullYear(), mtdFirstDate.getMonth() + 1, 0).getDate();
  const daysElapsed = mtd.daily_cy.length;
  const pacedRevenueBudget = daysInMonth ? budget.revenue * daysElapsed / daysInMonth : 0;
  const pacedAdSpendBudget = daysInMonth ? budget.ad_spend * daysElapsed / daysInMonth : 0;

  const revLyPct = calcPct(cy.revenue, ly.revenue);
  const revBudPct = calcPct(cy.revenue, pacedRevenueBudget);
  const ordLyPct = calcPct(cy.orders, ly.orders);
  const adLyPct = calcPct(cy.ad_spend, ly.ad_spend);
  const adBudPct = calcPct(cy.ad_spend, pacedAdSpendBudget);

  const projection = linearProjection(mtd.daily_cy);
  const runRate = trendRunRate(mtd.daily_cy);

  // MER floor = minimum MER for gross-profit break-even (1 / GM%)
  const merFloor = cy.gross_margin_pct ? 100 / cy.gross_margin_pct : null;
  const merHeadroom = cy.mer && merFloor ? cy.mer - merFloor : null;

  // Chart data: daily CY vs LY
  const lyMap: Record<number, number> = {};
  mtd.daily_ly.forEach(d => {
    const dt = new Date(d.date + 'T00:00:00');
    lyMap[dt.getDate()] = safe(d.revenue);
  });

  const dailyChartData = mtd.daily_cy.map(d => {
    const dt = new Date(d.date + 'T00:00:00');
    return {
      name: shortDate(d.date),
      cy: safe(d.revenue),
      ly: lyMap[dt.getDate()] ?? null,
    };
  });

  // Cumulative chart data
  const cyRevs = mtd.daily_cy.map(d => safe(d.revenue));
  const cyCum = cumulative(cyRevs);
  const lyRevs = mtd.daily_cy.map(d => {
    const dt = new Date(d.date + 'T00:00:00');
    return lyMap[dt.getDate()] ?? 0;
  });
  const lyCum = cumulative(lyRevs);

  const budgetDailyPace = daysInMonth ? budget.revenue / daysInMonth : 0;

  const cumulativeChartData = mtd.daily_cy.map((d, i) => ({
    name: shortDate(d.date),
    cy: cyCum[i],
    ly: lyCum[i],
    budget: Math.round(budgetDailyPace * (i + 1)),
  }));

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">MTD Overview</h1>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">As of {data.as_of}</span>
      </div>

      {/* Primary KPIs */}
      <KpiGrid columns={5}>
        <KpiCard
          label="Revenue"
          value={fmt(cy.revenue)}
          tooltip={sources.mtdRevenue}
          badges={[
            { label: `vs LY ${pct(revLyPct)}`, color: badgeColor(revLyPct) },
            { label: `vs Budget Pace ${pct(revBudPct)}`, color: badgeColor(revBudPct) },
          ]}
        />
        <KpiCard
          label="Orders"
          value={fmtInt(cy.orders)}
          tooltip={sources.mtdOrders}
          badges={[
            { label: `vs LY ${pct(ordLyPct)}`, color: badgeColor(ordLyPct) },
          ]}
        />
        <KpiCard
          label="Ad Spend"
          value={fmt(cy.ad_spend)}
          tooltip={sources.mtdAdSpend}
          badges={[
            { label: `vs LY ${pct(adLyPct)}`, color: badgeColor(adLyPct, false) },
            { label: `vs Budget Pace ${pct(adBudPct)}`, color: badgeColor(adBudPct, false) },
          ]}
        />
        <KpiCard
          label="MER"
          value={ratio(cy.mer)}
          tooltip={sources.mtdMer}
          badges={merHeadroom != null ? [{ label: `vs Floor ${merHeadroom >= 0 ? '+' : ''}${merHeadroom.toFixed(2)}x`, color: badgeColor(merHeadroom) }] : []}
          note={merFloor ? `Floor ${ratio(merFloor)}` : undefined}
        />
        <KpiCard
          label="AOV"
          value={fmt(cy.aov)}
          tooltip={sources.mtdAov}
        />
      </KpiGrid>

      {/* Month projections row */}
      {(projection || runRate) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
          {/* Simple pace */}
          {projection && (
            <div className="bg-surface-lowest rounded-xl shadow-ambient py-4 px-6">
              <div className="text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold mb-1 inline-flex items-center gap-1">
                Monthly Pace <InfoTooltip content={sources.mtdProjectedRevenue} />
              </div>
              <div className="text-2xl font-display font-bold text-brand-primary">{fmt(projection)}</div>
              <div className="text-xs text-brand-neutral/50 mt-1">based on daily average · {runRate?.daysElapsed ?? 0} of {runRate?.daysTotal ?? 30} days</div>
            </div>
          )}

          {/* Trend-adjusted run rate */}
          {runRate && (
            <div className="bg-surface-lowest rounded-xl shadow-ambient py-4 px-6">
              <div className="text-xs uppercase tracking-wider text-brand-neutral/50 font-semibold mb-1 inline-flex items-center gap-1">
                Month Run Rate
                <InfoTooltip content="Trend-adjusted projection using OLS regression on daily revenue. Blends full-month slope with recent 7-day slope, weighted by R² fit quality. Accounts for acceleration and deceleration within the month." />
              </div>
              <div className="text-2xl font-display font-bold text-brand-primary">{fmt(runRate.runRate)}</div>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-brand-neutral/60">
                <span className={runRate.recentTrendPerDay >= 0 ? 'text-brand-primary font-medium' : 'text-ns-red font-medium'}>
                  {runRate.recentTrendPerDay >= 0 ? '▲' : '▼'} {fmt(Math.abs(runRate.recentTrendPerDay))}/day recent
                </span>
                <span>·</span>
                <span className={runRate.trendPerDay >= 0 ? 'text-brand-primary' : 'text-ns-red'}>
                  {runRate.trendPerDay >= 0 ? '▲' : '▼'} {fmt(Math.abs(runRate.trendPerDay))}/day full-month
                </span>
                <span>·</span>
                <span>R² {(runRate.trendR2 * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Seasonality Index */}
      {seasonality?.index?.seasonality != null && (
        <div className="bg-surface-lowest rounded-xl shadow-ambient py-4 px-6 mb-8">
          <div className="flex flex-wrap items-center gap-x-8 gap-y-2 text-sm text-brand-neutral">
            <span className="inline-flex items-center gap-1.5">
              Seasonality Index:
              <strong className="text-brand-primary text-lg font-semibold">
                {seasonality.index.seasonality.toFixed(2)}
              </strong>
              <span className="text-xs text-brand-neutral/60 font-medium">{seasonality.index.label}</span>
              <InfoTooltip content="Dual-track 0–2 index (1 = average week of year). Demand: revenue + orders vs historical baseline. Performance: MER + Impression Share signals." />
            </span>
            <span className="text-brand-neutral/50 text-xs">
              Demand {seasonality.index.demand?.toFixed(2) ?? '—'} &nbsp;·&nbsp; Performance {seasonality.index.performance?.toFixed(2) ?? '—'} &nbsp;·&nbsp; Wk {seasonality.current_week}
            </span>
          </div>
        </div>
      )}

      {/* Detail KPIs in Accordion */}
      <Accordion className="mb-8">
        <AccordionItem>
          <AccordionHeading>
            <AccordionTrigger className="font-display text-lg font-semibold text-brand-neutral">
              Financial Details
            </AccordionTrigger>
          </AccordionHeading>
          <AccordionPanel>
            <AccordionBody>
              <KpiGrid columns={4}>
                <KpiCard label="COGS" value={fmt(cy.cogs)} tooltip={sources.mtdCogs} />
                <KpiCard label="Gross Profit" value={fmt(cy.gross_profit)} tooltip={sources.mtdGrossProfit} />
                <KpiCard label="Gross Margin %" value={cy.gross_margin_pct?.toFixed(1) + '%'} tooltip={sources.mtdGrossMarginPct} />
                <KpiCard label="Shipping" value={fmt(cy.shipping)} tooltip={sources.mtdShipping} />
                <KpiCard label="Platform Fees" value={fmt(cy.platform_fees)} tooltip={sources.mtdPlatformFees} />
                <KpiCard label="Net Revenue" value={fmt(cy.net_revenue)} tooltip={sources.mtdNetRevenue} />
                <KpiCard label="AOV" value={fmt(cy.aov)} tooltip={sources.mtdAov} />
                <KpiCard label="New Customer CAC" value={fmt(cy.new_customer_cac)} tooltip={sources.mtdNewCustomerCac} note={`${fmtInt(cy.new_customers)} new customers`} />
              </KpiGrid>
            </AccordionBody>
          </AccordionPanel>
        </AccordionItem>
      </Accordion>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <ChartCard title="Daily Revenue" tooltip={sources.dailyRevenueChart}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dailyChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#212529' }} interval="preserveStartEnd" />
              <YAxis tickFormatter={dollarFormatter} tick={{ fontSize: 10, fill: '#212529' }} />
              <Tooltip formatter={(v) => fmt(Number(v))} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="cy" name="CY Revenue" stroke="#2d6A4F" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="ly" name="LY Revenue" stroke="#52796F" strokeWidth={1.5} strokeDasharray="5 4" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Cumulative MTD Revenue" tooltip={sources.cumulativeRevenueChart}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={cumulativeChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#212529' }} interval="preserveStartEnd" />
              <YAxis tickFormatter={dollarFormatter} tick={{ fontSize: 10, fill: '#212529' }} />
              <Tooltip formatter={(v) => fmt(Number(v))} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area type="monotone" dataKey="cy" name="CY Cumulative" stroke="#2d6A4F" fill="rgba(45,106,79,0.1)" strokeWidth={2} />
              <Line type="monotone" dataKey="ly" name="LY Cumulative" stroke="#52796F" strokeWidth={1.5} strokeDasharray="5 4" dot={false} />
              <Line type="monotone" dataKey="budget" name="Budget Pace" stroke="#c96a2e" strokeWidth={1.5} strokeDasharray="2 3" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

    </div>
  );
}
