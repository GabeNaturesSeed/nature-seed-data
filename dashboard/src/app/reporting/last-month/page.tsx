'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { ReportingData } from '@/lib/types';
import { fmt, fmtInt, ratio, pct, calcPct, badgeColor, cumulative, safe, shortDate } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import ChartCard from '@/components/charts/ChartCard';
import { sources } from '@/lib/sources';
import { Skeleton, Accordion, AccordionItem, AccordionHeading, AccordionTrigger, AccordionPanel, AccordionBody } from '@heroui/react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  AreaChart, Area, ResponsiveContainer,
} from 'recharts';

const dollarFormatter = (v: number) => '$' + (v / 1000).toFixed(0) + 'K';

function monthLabel(dailyCy: { date: string }[]): string {
  if (!dailyCy.length) return 'Last Month';
  const d = new Date(dailyCy[0].date + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
}

export default function LastMonthPage() {
  const { data, loading } = useJsonData<ReportingData>('reporting');

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
  if (!data.lm) return <p className="text-brand-neutral/50">Last month data not yet available — regenerate reporting.json.</p>;

  const { lm } = data;
  const cy = lm.cy;
  const ly = lm.ly;
  const budget = lm.budget;

  // Last month is complete — compare vs full-month budget (no pacing needed)
  const revLyPct = calcPct(cy.revenue, ly.revenue);
  const revBudPct = calcPct(cy.revenue, budget.revenue);
  const ordLyPct = calcPct(cy.orders, ly.orders);
  const adLyPct = calcPct(cy.ad_spend, ly.ad_spend);
  const adBudPct = calcPct(cy.ad_spend, budget.ad_spend);

  const merFloor = cy.gross_margin_pct ? 100 / cy.gross_margin_pct : null;
  const merHeadroom = cy.mer && merFloor ? cy.mer - merFloor : null;

  // Chart data: daily CY vs LY aligned by day-of-month
  const lyMap: Record<number, number> = {};
  lm.daily_ly.forEach(d => {
    const dt = new Date(d.date + 'T00:00:00');
    lyMap[dt.getDate()] = safe(d.revenue);
  });

  const dailyChartData = lm.daily_cy.map(d => {
    const dt = new Date(d.date + 'T00:00:00');
    return {
      name: shortDate(d.date),
      cy: safe(d.revenue),
      ly: lyMap[dt.getDate()] ?? null,
    };
  });

  // Cumulative chart data
  const cyRevs = lm.daily_cy.map(d => safe(d.revenue));
  const cyCum = cumulative(cyRevs);
  const lyRevs = lm.daily_cy.map(d => {
    const dt = new Date(d.date + 'T00:00:00');
    return lyMap[dt.getDate()] ?? 0;
  });
  const lyCum = cumulative(lyRevs);
  const daysInMonth = lm.daily_cy.length || 30;
  const budgetDailyPace = budget.revenue / daysInMonth;

  const cumulativeChartData = lm.daily_cy.map((d, i) => ({
    name: shortDate(d.date),
    cy: cyCum[i],
    ly: lyCum[i],
    budget: Math.round(budgetDailyPace * (i + 1)),
  }));

  const label = monthLabel(lm.daily_cy);

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">Last Month — {label}</h1>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">Full month · as of {data.as_of}</span>
      </div>

      {/* Primary KPIs */}
      <KpiGrid columns={5}>
        <KpiCard
          label="Revenue"
          value={fmt(cy.revenue)}
          tooltip={sources.mtdRevenue}
          badges={[
            { label: `vs LY ${pct(revLyPct)}`, color: badgeColor(revLyPct) },
            { label: `vs Budget ${pct(revBudPct)}`, color: badgeColor(revBudPct) },
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
            { label: `vs Budget ${pct(adBudPct)}`, color: badgeColor(adBudPct, false) },
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

      {/* Financial Details */}
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

      {/* Charts */}
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

        <ChartCard title="Cumulative Revenue" tooltip={sources.cumulativeRevenueChart}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={cumulativeChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#212529' }} interval="preserveStartEnd" />
              <YAxis tickFormatter={dollarFormatter} tick={{ fontSize: 10, fill: '#212529' }} />
              <Tooltip formatter={(v) => fmt(Number(v))} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area type="monotone" dataKey="cy" name="CY Cumulative" stroke="#2d6A4F" fill="rgba(45,106,79,0.1)" strokeWidth={2} />
              <Line type="monotone" dataKey="ly" name="LY Cumulative" stroke="#52796F" strokeWidth={1.5} strokeDasharray="5 4" dot={false} />
              <Line type="monotone" dataKey="budget" name="Budget" stroke="#c96a2e" strokeWidth={1.5} strokeDasharray="2 3" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}
