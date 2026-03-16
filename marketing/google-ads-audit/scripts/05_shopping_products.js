/**
 * Script 5: Shopping Products (Aggregated)
 * Aggregates product-level Shopping/PMax data by QUARTER per product per campaign.
 * In-memory aggregation keeps row count within Sheet cell limits.
 * Critical for SKU normalization — preserves all product identifier fields.
 * Tab: Shopping_Products
 * Est. runtime: 10-20 min
 *
 * INSTRUCTIONS:
 * 1. Create a SECOND Google Sheet (Sheet 1 is full from Scripts 1-4)
 * 2. Paste that new Sheet URL below
 * 3. Go to Google Ads > Tools & Settings > Scripts
 * 4. Paste this entire script and click Run
 */

// ===================== CONFIG =====================
var CONFIG = {
  // >>> USE A NEW/SECOND GOOGLE SHEET — Sheet 1 hit the 10M cell limit <<<
  SPREADSHEET_URL: 'https://docs.google.com/spreadsheets/d/1eoGfHV6DmacNSM0TUA3RnjlZOiaRepzdCmeLR7o-DXU/edit',
  TAB_NAME: 'Shopping_Products',
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
    'Product Item ID',
    'Product Title',
    'Product Type (L1)',
    'Product Type (L2)',
    'Product Type (L3)',
    'Brand',
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
        "segments.quarter, " +
        "campaign.name, " +
        "campaign.id, " +
        "segments.product_item_id, " +
        "segments.product_title, " +
        "segments.product_type_l1, " +
        "segments.product_type_l2, " +
        "segments.product_type_l3, " +
        "segments.product_brand, " +
        "metrics.impressions, " +
        "metrics.clicks, " +
        "metrics.cost_micros, " +
        "metrics.conversions, " +
        "metrics.conversions_value " +
      "FROM shopping_performance_view " +
      "WHERE segments.date BETWEEN '" + chunk.start + "' AND '" + chunk.end + "' " +
      "ORDER BY segments.year, segments.quarter, metrics.cost_micros DESC";

    // Aggregate in memory: key = year|quarter|campaignId|productItemId
    var agg = {};
    var report = AdsApp.report(query);
    var reportRows = report.rows();

    while (reportRows.hasNext()) {
      var row = reportRows.next();

      var year = row['segments.year'];
      var quarter = row['segments.quarter'];
      var campId = row['campaign.id'];
      var itemId = row['segments.product_item_id'] || '';

      var key = year + '|' + quarter + '|' + campId + '|' + itemId;

      if (!agg[key]) {
        agg[key] = {
          year: year,
          quarter: 'Q' + quarter,
          campaignName: row['campaign.name'],
          campaignId: campId,
          itemId: itemId,
          title: row['segments.product_title'] || '',
          typeL1: row['segments.product_type_l1'] || '',
          typeL2: row['segments.product_type_l2'] || '',
          typeL3: row['segments.product_type_l3'] || '',
          brand: row['segments.product_brand'] || '',
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
        a.itemId,
        a.title,
        a.typeL1,
        a.typeL2,
        a.typeL3,
        a.brand,
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

    // Sort by cost descending
    rows.sort(function(a, b) {
      return parseFloat(b[13]) - parseFloat(a[13]);
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

    Logger.log('  Chunk done: ' + rows.length + ' aggregated rows.');
  }

  Logger.log('Shopping Products: ' + totalRows + ' total rows exported.');
}

// ===================== HELPERS =====================
function getOrCreateSheet(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
