/**
 * Script 7: Geo (State) & Device Performance
 * Pulls state-level geo performance + device breakdown.
 * Writes to TWO tabs: Geo_State_Perf and Device_Perf
 * Chunked by year to avoid 30-min timeout.
 * Est. runtime: 10-15 min
 *
 * INSTRUCTIONS:
 * 1. Paste your Google Sheet URL below
 * 2. Go to Google Ads > Tools & Settings > Scripts
 * 3. Paste this entire script and click Run
 */

// ===================== CONFIG =====================
var CONFIG = {
  // >>> USE THE SECOND GOOGLE SHEET (same as Script 5) <<<
  SPREADSHEET_URL: 'https://docs.google.com/spreadsheets/d/1eoGfHV6DmacNSM0TUA3RnjlZOiaRepzdCmeLR7o-DXU/edit',
  GEO_TAB: 'Geo_State_Perf',
  DEVICE_TAB: 'Device_Perf',
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

  pullGeoData(ss);
  pullDeviceData(ss);
}

function pullGeoData(ss) {
  var sheet = getOrCreateSheet(ss, CONFIG.GEO_TAB);

  var headers = [
    'Year',
    'Quarter',
    'State/Region',
    'Country',
    'Campaign Name',
    'Campaign ID',
    'Impressions',
    'Clicks',
    'CTR',
    'Cost ($)',
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
    Logger.log('Geo - Processing chunk: ' + chunk.start + ' to ' + chunk.end);

    // Use quarterly aggregation for geo to keep data manageable
    var query =
      "SELECT " +
        "segments.year, " +
        "segments.quarter, " +
        "geographic_view.country_criterion_id, " +
        "geographic_view.location_type, " +
        "campaign.name, " +
        "campaign.id, " +
        "metrics.impressions, " +
        "metrics.clicks, " +
        "metrics.ctr, " +
        "metrics.cost_micros, " +
        "metrics.conversions, " +
        "metrics.conversions_value " +
      "FROM geographic_view " +
      "WHERE segments.date BETWEEN '" + chunk.start + "' AND '" + chunk.end + "' " +
      "ORDER BY segments.year, segments.quarter, metrics.cost_micros DESC";

    var rows = [];
    var report = AdsApp.report(query);
    var reportRows = report.rows();

    while (reportRows.hasNext()) {
      var row = reportRows.next();

      var costMicros = parseInt(row['metrics.cost_micros'] || '0', 10);
      var cost = (costMicros / 1000000).toFixed(2);

      var conversionsValue = parseFloat(row['metrics.conversions_value'] || '0');
      var roas = costMicros > 0 ? (conversionsValue / (costMicros / 1000000)).toFixed(2) : '0.00';

      var ctr = row['metrics.ctr'] || '0';
      if (typeof ctr === 'string' && ctr.indexOf('%') === -1) {
        ctr = (parseFloat(ctr) * 100).toFixed(2) + '%';
      }

      rows.push([
        row['segments.year'],
        'Q' + row['segments.quarter'],
        row['geographic_view.location_type'] || '',
        row['geographic_view.country_criterion_id'] || '',
        row['campaign.name'],
        row['campaign.id'],
        row['metrics.impressions'],
        row['metrics.clicks'],
        ctr,
        cost,
        parseFloat(row['metrics.conversions'] || '0').toFixed(2),
        conversionsValue.toFixed(2),
        roas
      ]);
    }

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

    Logger.log('  Geo chunk done: ' + rows.length + ' rows.');
  }

  Logger.log('Geo Performance: ' + totalRows + ' total rows exported.');
}

function pullDeviceData(ss) {
  var sheet = getOrCreateSheet(ss, CONFIG.DEVICE_TAB);

  var headers = [
    'Year',
    'Month',
    'Device',
    'Campaign Name',
    'Campaign ID',
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
    Logger.log('Device - Processing chunk: ' + chunk.start + ' to ' + chunk.end);

    var query =
      "SELECT " +
        "segments.year, " +
        "segments.month, " +
        "segments.device, " +
        "campaign.name, " +
        "campaign.id, " +
        "metrics.impressions, " +
        "metrics.clicks, " +
        "metrics.ctr, " +
        "metrics.cost_micros, " +
        "metrics.average_cpc, " +
        "metrics.conversions, " +
        "metrics.conversions_value " +
      "FROM campaign " +
      "WHERE segments.date BETWEEN '" + chunk.start + "' AND '" + chunk.end + "' " +
      "ORDER BY segments.year, segments.month, campaign.name, segments.device";

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
        row['segments.device'],
        row['campaign.name'],
        row['campaign.id'],
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

    if (rows.length > 0) {
      var startRow = sheet.getLastRow() + 1;
      sheet.getRange(startRow, 1, rows.length, headers.length).setValues(rows);
      totalRows += rows.length;
    }

    Logger.log('  Device chunk done: ' + rows.length + ' rows.');
  }

  Logger.log('Device Performance: ' + totalRows + ' total rows exported.');
}

// ===================== HELPERS =====================
function getOrCreateSheet(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
