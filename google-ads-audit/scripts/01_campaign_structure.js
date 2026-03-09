/**
 * Script 1: Campaign Structure
 * Pulls all campaigns (active, paused, removed) with type, bidding, budget, dates.
 * Tab: Campaigns_Structure
 * Est. runtime: 2-5 min
 *
 * INSTRUCTIONS:
 * 1. Paste your Google Sheet URL below
 * 2. Go to Google Ads > Tools & Settings > Scripts
 * 3. Paste this entire script and click Run
 */

// ===================== CONFIG =====================
var CONFIG = {
  SPREADSHEET_URL: 'https://docs.google.com/spreadsheets/d/1pxIpjA8NGI7bM1JkANXtkJ1anpCOQ-Cs7-eQVnAit5k/edit',
  TAB_NAME: 'Campaigns_Structure'
};
// ==================================================

function main() {
  var ss = SpreadsheetApp.openByUrl(CONFIG.SPREADSHEET_URL);
  var sheet = getOrCreateSheet(ss, CONFIG.TAB_NAME);

  var headers = [
    'Campaign ID',
    'Campaign Name',
    'Status',
    'Channel Type',
    'Sub Type',
    'Bidding Strategy',
    'Budget ($/day)',
    'Budget Delivery',
    'Start Date',
    'End Date',
    'Labels',
    'Serving Status',
    'Optimization Score'
  ];

  sheet.clear();
  sheet.appendRow(headers);
  sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');

  var query =
    "SELECT " +
      "campaign.id, " +
      "campaign.name, " +
      "campaign.status, " +
      "campaign.advertising_channel_type, " +
      "campaign.advertising_channel_sub_type, " +
      "campaign.bidding_strategy_type, " +
      "campaign_budget.amount_micros, " +
      "campaign_budget.delivery_method, " +
      "campaign.start_date, " +
      "campaign.end_date, " +
      "campaign.labels, " +
      "campaign.serving_status, " +
      "campaign.optimization_score " +
    "FROM campaign " +
    "ORDER BY campaign.name";

  var rows = [];
  var report = AdsApp.report(query);
  var reportRows = report.rows();

  while (reportRows.hasNext()) {
    var row = reportRows.next();

    var budgetMicros = row['campaign_budget.amount_micros'] || '0';
    var budgetDollars = (parseInt(budgetMicros, 10) / 1000000).toFixed(2);

    var labels = row['campaign.labels'];
    if (labels && labels !== '--') {
      // labels may be returned as an array or string depending on API version
      if (Array.isArray(labels)) {
        labels = labels.join(', ');
      } else {
        labels = String(labels).replace(/\[|\]/g, '').replace(/"/g, '');
      }
    } else {
      labels = '';
    }

    rows.push([
      row['campaign.id'],
      row['campaign.name'],
      row['campaign.status'],
      row['campaign.advertising_channel_type'],
      row['campaign.advertising_channel_sub_type'] || '',
      row['campaign.bidding_strategy_type'],
      budgetDollars,
      row['campaign_budget.delivery_method'] || '',
      row['campaign.start_date'] || '',
      row['campaign.end_date'] || '',
      labels,
      row['campaign.serving_status'] || '',
      row['campaign.optimization_score'] || ''
    ]);
  }

  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }

  Logger.log('Campaign Structure: ' + rows.length + ' campaigns exported.');
}

// ===================== HELPERS =====================
function getOrCreateSheet(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
