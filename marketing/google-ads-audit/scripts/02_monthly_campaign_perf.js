/**
 * Script 2: Monthly Campaign Performance
 * Pulls monthly metrics per campaign: impressions, clicks, cost, conversions, revenue, ROAS.
 * Chunked by year to avoid 30-min timeout.
 * Tab: Monthly_Campaign_Perf
 * Est. runtime: 10-15 min
 *
 * INSTRUCTIONS:
 * 1. Paste your Google Sheet URL below
 * 2. Go to Google Ads > Tools & Settings > Scripts
 * 3. Paste this entire script and click Run
 */

// ===================== CONFIG =====================
var CONFIG = {
  SPREADSHEET_URL: 'https://docs.google.com/spreadsheets/d/1pxIpjA8NGI7bM1JkANXtkJ1anpCOQ-Cs7-eQVnAit5k/edit',
  TAB_NAME: 'Monthly_Campaign_Perf',
  YEAR_RANGES: [
    { start: '2022-03-01', end: '2022-12-31' },
    { start: '2023-01-01', end: '2023-12-31' },
    { start: '2024-01-01', end: '2024-12-31' },
    { start: '2025-01-01', end: '2025-12-31' },
    { start: '2026-01-01', end: '2026-03-04' }
  ]
};
// ==================================================

function main() {
  var ss = SpreadsheetApp.openByUrl(CONFIG.SPREADSHEET_URL);
  var sheet = getOrCreateSheet(ss, CONFIG.TAB_NAME);

  var headers = [
    'Year',
    'Month',
    'Campaign ID',
    'Campaign Name',
    'Campaign Status',
    'Channel Type',
    'Impressions',
    'Clicks',
    'CTR',
    'Cost ($)',
    'Avg CPC ($)',
    'Conversions',
    'Conv. Value ($)',
    'Cost/Conv ($)',
    'ROAS',
    'Search Impr. Share',
    'Search Lost IS (Budget)',
    'Search Lost IS (Rank)',
    'Interactions',
    'Interaction Rate'
  ];

  sheet.clear();
  sheet.appendRow(headers);
  sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');

  var totalRows = 0;

  for (var c = 0; c < CONFIG.YEAR_RANGES.length; c++) {
    var chunk = CONFIG.YEAR_RANGES[c];
    Logger.log('Processing chunk: ' + chunk.start + ' to ' + chunk.end);

    var query =
      "SELECT " +
        "segments.year, " +
        "segments.month, " +
        "campaign.id, " +
        "campaign.name, " +
        "campaign.status, " +
        "campaign.advertising_channel_type, " +
        "metrics.impressions, " +
        "metrics.clicks, " +
        "metrics.ctr, " +
        "metrics.cost_micros, " +
        "metrics.average_cpc, " +
        "metrics.conversions, " +
        "metrics.conversions_value, " +
        "metrics.cost_per_conversion, " +
        "metrics.search_impression_share, " +
        "metrics.search_budget_lost_impression_share, " +
        "metrics.search_rank_lost_impression_share, " +
        "metrics.interactions, " +
        "metrics.interaction_rate " +
      "FROM campaign " +
      "WHERE segments.date BETWEEN '" + chunk.start + "' AND '" + chunk.end + "' " +
      "ORDER BY segments.year, segments.month, campaign.name";

    var rows = [];
    var report = AdsApp.report(query);
    var reportRows = report.rows();

    while (reportRows.hasNext()) {
      var row = reportRows.next();

      var costMicros = parseInt(row['metrics.cost_micros'] || '0', 10);
      var cost = (costMicros / 1000000).toFixed(2);

      var avgCpcMicros = parseInt(row['metrics.average_cpc'] || '0', 10);
      var avgCpc = (avgCpcMicros / 1000000).toFixed(2);

      var costPerConvMicros = parseInt(row['metrics.cost_per_conversion'] || '0', 10);
      var costPerConv = (costPerConvMicros / 1000000).toFixed(2);

      var conversionsValue = parseFloat(row['metrics.conversions_value'] || '0');
      var roas = costMicros > 0 ? (conversionsValue / (costMicros / 1000000)).toFixed(2) : '0.00';

      var ctr = row['metrics.ctr'] || '0';
      if (typeof ctr === 'string' && ctr.indexOf('%') === -1) {
        ctr = (parseFloat(ctr) * 100).toFixed(2) + '%';
      }

      var interactionRate = row['metrics.interaction_rate'] || '0';
      if (typeof interactionRate === 'string' && interactionRate.indexOf('%') === -1) {
        interactionRate = (parseFloat(interactionRate) * 100).toFixed(2) + '%';
      }

      rows.push([
        row['segments.year'],
        row['segments.month'],
        row['campaign.id'],
        row['campaign.name'],
        row['campaign.status'],
        row['campaign.advertising_channel_type'],
        row['metrics.impressions'],
        row['metrics.clicks'],
        ctr,
        cost,
        avgCpc,
        parseFloat(row['metrics.conversions'] || '0').toFixed(2),
        conversionsValue.toFixed(2),
        costPerConv,
        roas,
        row['metrics.search_impression_share'] || '',
        row['metrics.search_budget_lost_impression_share'] || '',
        row['metrics.search_rank_lost_impression_share'] || '',
        row['metrics.interactions'] || '0',
        interactionRate
      ]);
    }

    if (rows.length > 0) {
      var startRow = sheet.getLastRow() + 1;
      sheet.getRange(startRow, 1, rows.length, headers.length).setValues(rows);
      totalRows += rows.length;
    }

    Logger.log('  Chunk done: ' + rows.length + ' rows.');
  }

  Logger.log('Monthly Campaign Perf: ' + totalRows + ' total rows exported.');
}

// ===================== HELPERS =====================
function getOrCreateSheet(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
