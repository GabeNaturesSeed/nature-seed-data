/**
 * Script 3: Ad Groups & Keywords
 * Pulls keyword-level monthly performance with quality score and match type.
 * Chunked by year to avoid 30-min timeout.
 * Tab: AdGroups_Keywords
 * Est. runtime: 15-25 min
 *
 * INSTRUCTIONS:
 * 1. Paste your Google Sheet URL below
 * 2. Go to Google Ads > Tools & Settings > Scripts
 * 3. Paste this entire script and click Run
 */

// ===================== CONFIG =====================
var CONFIG = {
  SPREADSHEET_URL: 'https://docs.google.com/spreadsheets/d/1pxIpjA8NGI7bM1JkANXtkJ1anpCOQ-Cs7-eQVnAit5k/edit',
  TAB_NAME: 'AdGroups_Keywords',
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
    'Campaign Name',
    'Campaign ID',
    'Ad Group Name',
    'Ad Group ID',
    'Keyword Text',
    'Match Type',
    'Keyword Status',
    'Quality Score',
    'Expected CTR',
    'Ad Relevance',
    'Landing Page Exp.',
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

    var query =
      "SELECT " +
        "segments.year, " +
        "segments.month, " +
        "campaign.name, " +
        "campaign.id, " +
        "ad_group.name, " +
        "ad_group.id, " +
        "ad_group_criterion.keyword.text, " +
        "ad_group_criterion.keyword.match_type, " +
        "ad_group_criterion.status, " +
        "ad_group_criterion.quality_info.quality_score, " +
        "ad_group_criterion.quality_info.creative_quality_score, " +
        "ad_group_criterion.quality_info.post_click_quality_score, " +
        "ad_group_criterion.quality_info.search_predicted_ctr, " +
        "metrics.impressions, " +
        "metrics.clicks, " +
        "metrics.ctr, " +
        "metrics.cost_micros, " +
        "metrics.average_cpc, " +
        "metrics.conversions, " +
        "metrics.conversions_value " +
      "FROM keyword_view " +
      "WHERE segments.date BETWEEN '" + chunk.start + "' AND '" + chunk.end + "' " +
      "ORDER BY segments.year, segments.month, campaign.name, ad_group.name";

    var rows = [];
    var report = AdsApp.report(query);
    var reportRows = report.rows();

    while (reportRows.hasNext()) {
      var row = reportRows.next();

      var costMicros = parseInt(row['metrics.cost_micros'] || '0', 10);
      var cost = (costMicros / 1000000).toFixed(2);

      var avgCpcMicros = parseInt(row['metrics.average_cpc'] || '0', 10);
      var avgCpc = (avgCpcMicros / 1000000).toFixed(2);

      var conversionsValue = parseFloat(row['metrics.conversions_value'] || '0');
      var roas = costMicros > 0 ? (conversionsValue / (costMicros / 1000000)).toFixed(2) : '0.00';

      var ctr = row['metrics.ctr'] || '0';
      if (typeof ctr === 'string' && ctr.indexOf('%') === -1) {
        ctr = (parseFloat(ctr) * 100).toFixed(2) + '%';
      }

      rows.push([
        row['segments.year'],
        row['segments.month'],
        row['campaign.name'],
        row['campaign.id'],
        row['ad_group.name'],
        row['ad_group.id'],
        row['ad_group_criterion.keyword.text'] || '',
        row['ad_group_criterion.keyword.match_type'] || '',
        row['ad_group_criterion.status'] || '',
        row['ad_group_criterion.quality_info.quality_score'] || '',
        row['ad_group_criterion.quality_info.search_predicted_ctr'] || '',
        row['ad_group_criterion.quality_info.creative_quality_score'] || '',
        row['ad_group_criterion.quality_info.post_click_quality_score'] || '',
        row['metrics.impressions'],
        row['metrics.clicks'],
        ctr,
        cost,
        avgCpc,
        parseFloat(row['metrics.conversions'] || '0').toFixed(2),
        conversionsValue.toFixed(2),
        roas
      ]);
    }

    // Write in batches to avoid memory issues
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

    Logger.log('  Chunk done: ' + rows.length + ' rows.');
  }

  Logger.log('Ad Groups & Keywords: ' + totalRows + ' total rows exported.');
}

// ===================== HELPERS =====================
function getOrCreateSheet(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
