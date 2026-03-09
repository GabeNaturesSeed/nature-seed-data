/**
 * Script 4: Search Terms (Aggregated)
 * Aggregates search terms by QUARTER (not month) to stay within Sheet cell limits.
 * Groups by: Year, Quarter, Campaign, Search Term — sums metrics.
 * Only includes terms with at least 1 click to filter impression-only noise.
 * Tab: Search_Terms
 * Est. runtime: 15-25 min
 *
 * INSTRUCTIONS:
 * 1. Go to Google Ads > Tools & Settings > Scripts
 * 2. Paste this entire script and click Run
 * 3. If it STILL hits the cell limit, increase MIN_CLICKS to 2
 */

// ===================== CONFIG =====================
var CONFIG = {
  SPREADSHEET_URL: 'https://docs.google.com/spreadsheets/d/1pxIpjA8NGI7bM1JkANXtkJ1anpCOQ-Cs7-eQVnAit5k/edit',
  TAB_NAME: 'Search_Terms',
  MIN_CLICKS: 1, // Only include terms with at least this many clicks (per quarter)
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
    'Quarter',
    'Campaign Name',
    'Campaign ID',
    'Search Term',
    'Impressions',
    'Clicks',
    'CTR',
    'Cost ($)',
    'Avg CPC ($)',
    'Conversions',
    'Conv. Value ($)',
    'ROAS'
  ];

  sheet.clear();
  sheet.appendRow(headers);
  sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');

  var totalRows = 0;

  for (var c = 0; c < CONFIG.YEAR_RANGES.length; c++) {
    var chunk = CONFIG.YEAR_RANGES[c];
    Logger.log('Processing chunk: ' + chunk.start + ' to ' + chunk.end);

    // Use quarterly segmentation and require clicks >= MIN_CLICKS
    var query =
      "SELECT " +
        "segments.year, " +
        "segments.quarter, " +
        "campaign.name, " +
        "campaign.id, " +
        "search_term_view.search_term, " +
        "metrics.impressions, " +
        "metrics.clicks, " +
        "metrics.ctr, " +
        "metrics.cost_micros, " +
        "metrics.average_cpc, " +
        "metrics.conversions, " +
        "metrics.conversions_value " +
      "FROM search_term_view " +
      "WHERE segments.date BETWEEN '" + chunk.start + "' AND '" + chunk.end + "' " +
        "AND metrics.clicks >= " + CONFIG.MIN_CLICKS + " " +
      "ORDER BY segments.year, segments.quarter, metrics.cost_micros DESC";

    // Aggregate in memory: key = year|quarter|campaignId|searchTerm
    var agg = {};
    var report = AdsApp.report(query);
    var reportRows = report.rows();

    while (reportRows.hasNext()) {
      var row = reportRows.next();

      var year = row['segments.year'];
      var quarter = row['segments.quarter'];
      var campName = row['campaign.name'];
      var campId = row['campaign.id'];
      var term = row['search_term_view.search_term'];

      var key = year + '|' + quarter + '|' + campId + '|' + term;

      if (!agg[key]) {
        agg[key] = {
          year: year,
          quarter: 'Q' + quarter,
          campaignName: campName,
          campaignId: campId,
          searchTerm: term,
          impressions: 0,
          clicks: 0,
          costMicros: 0,
          conversions: 0,
          convValue: 0
        };
      }

      agg[key].impressions += parseInt(row['metrics.impressions'] || '0', 10);
      agg[key].clicks += parseInt(row['metrics.clicks'] || '0', 10);
      agg[key].costMicros += parseInt(row['metrics.cost_micros'] || '0', 10);
      agg[key].conversions += parseFloat(row['metrics.conversions'] || '0');
      agg[key].convValue += parseFloat(row['metrics.conversions_value'] || '0');
    }

    // Convert aggregated data to rows
    var rows = [];
    var keys = Object.keys(agg);
    for (var i = 0; i < keys.length; i++) {
      var a = agg[keys[i]];
      var cost = a.costMicros / 1000000;
      var avgCpc = a.clicks > 0 ? (cost / a.clicks) : 0;
      var ctr = a.impressions > 0 ? (a.clicks / a.impressions * 100) : 0;
      var roas = cost > 0 ? (a.convValue / cost) : 0;

      rows.push([
        a.year,
        a.quarter,
        a.campaignName,
        a.campaignId,
        a.searchTerm,
        a.impressions,
        a.clicks,
        ctr.toFixed(2) + '%',
        cost.toFixed(2),
        avgCpc.toFixed(2),
        a.conversions.toFixed(2),
        a.convValue.toFixed(2),
        roas.toFixed(2)
      ]);
    }

    // Sort by cost descending within this chunk
    rows.sort(function(a, b) {
      return parseFloat(b[8]) - parseFloat(a[8]);
    });

    // Write in batches
    if (rows.length > 0) {
      var batchSize = 10000;
      for (var b = 0; b < rows.length; b += batchSize) {
        var batch = rows.slice(b, Math.min(b + batchSize, rows.length));
        var startRow = sheet.getLastRow() + 1;
        sheet.getRange(startRow, 1, batch.length, headers.length).setValues(batch);
        SpreadsheetApp.flush();
      }
      totalRows += rows.length;
    }

    Logger.log('  Chunk done: ' + rows.length + ' aggregated rows (from ' + keys.length + ' unique terms).');
  }

  Logger.log('Search Terms: ' + totalRows + ' total rows exported.');
}

// ===================== HELPERS =====================
function getOrCreateSheet(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
