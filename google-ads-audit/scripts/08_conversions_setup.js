/**
 * Script 8: Conversions Setup
 * Pulls all conversion actions with attribution model, counting type, status.
 * Run this FIRST to understand what "conversions" means in this account.
 * Tab: Conversions_Setup
 * Est. runtime: 2-5 min
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
  TAB_NAME: 'Conversions_Setup'
};
// ==================================================

function main() {
  var ss = SpreadsheetApp.openByUrl(CONFIG.SPREADSHEET_URL);
  var sheet = getOrCreateSheet(ss, CONFIG.TAB_NAME);

  var headers = [
    'Conversion Action ID',
    'Conversion Action Name',
    'Category',
    'Status',
    'Counting Type',
    'Attribution Model',
    'Include in Conversions',
    'Include in Conversions Bidding',
    'Click-Through Lookback (days)',
    'View-Through Lookback (days)',
    'Value Settings - Default Value',
    'Value Settings - Always Use Default',
    'Origin',
    'Type',
    'Owner Customer ID'
  ];

  sheet.clear();
  sheet.appendRow(headers);
  sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');

  var query =
    "SELECT " +
      "conversion_action.id, " +
      "conversion_action.name, " +
      "conversion_action.category, " +
      "conversion_action.status, " +
      "conversion_action.counting_type, " +
      "conversion_action.attribution_model_settings.attribution_model, " +
      "conversion_action.include_in_conversions_metric, " +
      "conversion_action.primary_for_goal, " +
      "conversion_action.click_through_lookback_window_days, " +
      "conversion_action.view_through_lookback_window_days, " +
      "conversion_action.value_settings.default_value, " +
      "conversion_action.value_settings.always_use_default_value, " +
      "conversion_action.origin, " +
      "conversion_action.type, " +
      "conversion_action.owner_customer " +
    "FROM conversion_action " +
    "ORDER BY conversion_action.name";

  var rows = [];
  var report = AdsApp.report(query);
  var reportRows = report.rows();

  while (reportRows.hasNext()) {
    var row = reportRows.next();

    rows.push([
      row['conversion_action.id'],
      row['conversion_action.name'],
      row['conversion_action.category'] || '',
      row['conversion_action.status'],
      row['conversion_action.counting_type'] || '',
      row['conversion_action.attribution_model_settings.attribution_model'] || '',
      row['conversion_action.include_in_conversions_metric'] || '',
      row['conversion_action.primary_for_goal'] || '',
      row['conversion_action.click_through_lookback_window_days'] || '',
      row['conversion_action.view_through_lookback_window_days'] || '',
      row['conversion_action.value_settings.default_value'] || '',
      row['conversion_action.value_settings.always_use_default_value'] || '',
      row['conversion_action.origin'] || '',
      row['conversion_action.type'] || '',
      row['conversion_action.owner_customer'] || ''
    ]);
  }

  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }

  // --- Also add a summary of recent conversion volumes ---
  Logger.log('Pulling conversion volume summary...');

  var summarySheet = getOrCreateSheet(ss, 'Conversions_Volume_Summary');
  var summaryHeaders = [
    'Year',
    'Quarter',
    'Conversion Action Name',
    'All Conversions',
    'All Conv. Value ($)'
  ];

  summarySheet.clear();
  summarySheet.appendRow(summaryHeaders);
  summarySheet.getRange(1, 1, 1, summaryHeaders.length).setFontWeight('bold');

  var summaryQuery =
    "SELECT " +
      "segments.year, " +
      "segments.quarter, " +
      "segments.conversion_action_name, " +
      "metrics.all_conversions, " +
      "metrics.all_conversions_value " +
    "FROM campaign " +
    "WHERE segments.date BETWEEN '2022-03-01' AND '2026-03-04' " +
    "ORDER BY segments.year, segments.quarter, segments.conversion_action_name";

  var summaryRows = [];
  var summaryReport = AdsApp.report(summaryQuery);
  var summaryReportRows = summaryReport.rows();

  // Aggregate by year + quarter + conversion action
  var agg = {};
  while (summaryReportRows.hasNext()) {
    var srow = summaryReportRows.next();
    var key = srow['segments.year'] + '|Q' + srow['segments.quarter'] + '|' +
              srow['segments.conversion_action_name'];

    if (!agg[key]) {
      agg[key] = {
        year: srow['segments.year'],
        quarter: 'Q' + srow['segments.quarter'],
        action: srow['segments.conversion_action_name'],
        conversions: 0,
        value: 0
      };
    }
    agg[key].conversions += parseFloat(srow['metrics.all_conversions'] || '0');
    agg[key].value += parseFloat(srow['metrics.all_conversions_value'] || '0');
  }

  var aggKeys = Object.keys(agg).sort();
  for (var i = 0; i < aggKeys.length; i++) {
    var a = agg[aggKeys[i]];
    summaryRows.push([
      a.year,
      a.quarter,
      a.action,
      a.conversions.toFixed(2),
      a.value.toFixed(2)
    ]);
  }

  if (summaryRows.length > 0) {
    summarySheet.getRange(2, 1, summaryRows.length, summaryHeaders.length).setValues(summaryRows);
  }

  Logger.log('Conversions Setup: ' + rows.length + ' actions exported.');
  Logger.log('Conversions Volume Summary: ' + summaryRows.length + ' rows exported.');
}

// ===================== HELPERS =====================
function getOrCreateSheet(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
