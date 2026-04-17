'use client';

import { useJsonData } from '@/hooks/useJsonData';
import { ReportingData } from '@/lib/types';
import { fmt, fmtInt, ratio, pct, calcPct, badgeColor, linearProjection, cumulative, safe, shortDate } from '@/lib/formatters';
import KpiCard from '@/components/kpi/KpiCard';
import KpiGrid from '@/components/kpi/KpiGrid';
import ChartCard from '@/components/charts/ChartCard';
import { sources } from '@/lib/sources';
import InfoTooltip from '@/components/InfoTooltip';
import { Skeleton, Accordion, AccordionItem, AccordionHeading, AccordionTrigger, AccordionPanel, AccordionBody } from '@heroui/react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  AreaChart, Area, ResponsiveContainer,
} from 'recharts';

const dollarFormatter = (v: number) => '$' + (v / 1000).toFixed(0) + 'K';

export default function ReportingMtdPage() {
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

  const { mtd } = data;
  const cy = mtd.cy;
  const ly = mtd.ly;
  const budget = mtd.budget;

  const revLyPct = calcPct(cy.revenue, ly.revenue);
  const revBudPct = calcPct(cy.revenue, budget.revenue);
  const ordLyPct = calcPct(cy.orders, ly.orders);
  const adLyPct = calcPct(cy.ad_spend, ly.ad_spend);
  const adBudPct = calcPct(cy.ad_spend, budget.ad_spend);

  const projection = linearProjection(mtd.daily_cy);

  // CM2 projections: use CM2% as a constant rate applied to projected revenue
  const cm2PctRate = safe(cy.cm2_pct) / 100;
  const projectedCM2 = projection ? projection * cm2PctRate : null;
  const projectedCM2Pct = cy.cm2_pct;

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

  const firstDate = mtd.daily_cy.length ? new Date(mtd.daily_cy[0].date + 'T00:00:00') : new Date();
  const dim = new Date(firstDate.getFullYear(), firstDate.getMonth() + 1, 0).getDate();
  const budgetDailyPace = budget.revenue / dim;

  const cumulativeChartData = mtd.daily_cy.map((d, i) => ({
    name: shortDate(d.date),
    cy: cyCum[i],
    ly: lyCum[i],
    budget: Math.round(budgetDailyPace * (i + 1)),
  }));

  // Daily CM chart data: approximate daily CM using MTD CM2% rate
  const dailyCMChartData = mtd.daily_cy.map(d => ({
    name: shortDate(d.date),
    cm: Math.round(safe(d.revenue) * cm2PctRate),
  }));

  // Cumulative CM chart data: running sum of daily CM
  const dailyCMValues = mtd.daily_cy.map(d => safe(d.revenue) * cm2PctRate);
  const cyCMCum = cumulative(dailyCMValues);
  // LY cumulative CM: use same CM% rate as approximation (LY CM% not available)
  const lyCMValues = mtd.daily_cy.map(d => {
    const dt = new Date(d.date + 'T00:00:00');
    return (lyMap[dt.getDate()] ?? 0) * cm2PctRate;
  });
  const lyCMCum = cumulative(lyCMValues);

  const cumulativeCMChartData = mtd.daily_cy.map((d, i) => ({
    name: shortDate(d.date),
    cy: Math.round(cyCMCum[i]),
    ly: Math.round(lyCMCum[i]),
  }));

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6 md:mb-8">
        <h1 className="text-xl md:text-2xl font-display font-bold text-brand-neutral">MTD Overview</h1>
        <span className="text-[10px] md:text-xs text-brand-neutral/50">As of {data.as_of}</span>
      </div>

      {/* Primary KPIs */}
      <KpiGrid columns={3}>
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
          label="CM2 $"
          value={fmt(cy.cm2)}
          tooltip={sources.mtdCm2}
          note="Revenue less COGS, shipping, ads, fees"
        />
        <KpiCard
          label="CM2 %"
          value={cy.cm2_pct?.toFixed(1) + '%'}
          tooltip={sources.mtdCm2Pct}
          badges={[
            { label: cy.cm2_pct >= 20 ? 'Healthy' : cy.cm2_pct >= 10 ? 'Marginal' : 'Below Target', color: cy.cm2_pct >= 20 ? 'success' : cy.cm2_pct >= 10 ? 'warning' : 'danger' },
          ]}
        />
      </KpiGrid>

      <KpiGrid columns={4}>
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
        />
        <KpiCard
          label="AOV"
          value={fmt(cy.aov)}
          tooltip={sources.mtdAov}
        />
      </KpiGrid>

      {/* Projection bar */}
      {projection && (
        <div className="bg-surface-lowest rounded-xl shadow-ambient py-4 px-6 mb-8">
          <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm text-brand-neutral items-center">
            <span className="inline-flex items-center gap-1.5">
              Projected Revenue: <strong className="text-brand-primary text-lg font-semibold">{fmt(projection)}</strong>
              <InfoTooltip content={sources.mtdProjectedRevenue} />
            </span>
            <span className="inline-flex items-center gap-1.5">
              Projected CM2 $: <strong className="text-lg font-semibold" style={{ color: '#c96a2e' }}>{fmt(projectedCM2)}</strong>
              <InfoTooltip content={sources.mtdProjectedCm2} />
            </span>
            <span>
              Projected CM2 %: <strong className="text-lg font-semibold" style={{ color: '#c96a2e' }}>{projectedCM2Pct?.toFixed(1)}%</strong>
            </span>
            <span className="text-brand-neutral/50">based on current daily pace</span>
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
              <KpiGrid columns={5}>
                <KpiCard label="COGS" value={fmt(cy.cogs)} tooltip={sources.mtdCogs} />
                <KpiCard label="Gross Profit" value={fmt(cy.gross_profit)} tooltip={sources.mtdGrossProfit} />
                <KpiCard label="Gross Margin %" value={cy.gross_margin_pct?.toFixed(1) + '%'} tooltip={sources.mtdGrossMarginPct} />
                <KpiCard label="CM2" value={fmt(cy.cm2)} tooltip={sources.mtdCm2} />
                <KpiCard label="CM2 %" value={cy.cm2_pct?.toFixed(1) + '%'} tooltip={sources.mtdCm2Pct} />
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

      {/* Contribution Margin Charts */}
      <h2 className="font-display text-lg font-semibold text-brand-neutral mb-4">Contribution Margin</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <ChartCard title="Daily Contribution Margin" tooltip={sources.dailyCmChart}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={dailyCMChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#212529' }} interval="preserveStartEnd" />
              <YAxis tickFormatter={dollarFormatter} tick={{ fontSize: 10, fill: '#212529' }} />
              <Tooltip formatter={(v) => fmt(Number(v))} />
              <Bar dataKey="cm" name="Daily CM2" fill="#c96a2e" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Cumulative MTD Contribution Margin" tooltip={sources.cumulativeCmChart}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={cumulativeCMChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(191,201,193,0.1)" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#212529' }} interval="preserveStartEnd" />
              <YAxis tickFormatter={dollarFormatter} tick={{ fontSize: 10, fill: '#212529' }} />
              <Tooltip formatter={(v) => fmt(Number(v))} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="cy" name="CY CM2" stroke="#c96a2e" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="ly" name="LY CM2 (est.)" stroke="#e0965c" strokeWidth={1.5} strokeDasharray="5 4" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

    </div>
  );
}
