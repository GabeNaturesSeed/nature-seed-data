/**
 * Script 6: Ad Copy Performance
 * Pulls headlines, descriptions, final URLs, CTR, conversions per ad.
 * Aggregated over full 4-year period (not monthly — keeps data manageable).
 * Tab: Ad_Copy_Perf
 * Est. runtime: 5-10 min
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
  TAB_NAME: 'Ad_Copy_Perf',
  DATE_START: '2022-03-01',
  DATE_END: '2026-03-04'
};
// ==================================================

function main() {
  var ss = SpreadsheetApp.openByUrl(CONFIG.SPREADSHEET_URL);
  var sheet = getOrCreateSheet(ss, CONFIG.TAB_NAME);

  var headers = [
    'Campaign Name',
    'Campaign ID',
    'Ad Group Name',
    'Ad Group ID',
    'Ad ID',
    'Ad Type',
    'Ad Status',
    'Final URL',
    'Headline 1',
    'Headline 2',
    'Headline 3',
    'Description 1',
    'Description 2',
    'Path 1',
    'Path 2',
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

  // --- Responsive Search Ads (RSAs) ---
  Logger.log('Pulling Responsive Search Ads...');
  var rsaQuery =
    "SELECT " +
      "campaign.name, " +
      "campaign.id, " +
      "ad_group.name, " +
      "ad_group.id, " +
      "ad_group_ad.ad.id, " +
      "ad_group_ad.ad.type, " +
      "ad_group_ad.status, " +
      "ad_group_ad.ad.final_urls, " +
      "ad_group_ad.ad.responsive_search_ad.headlines, " +
      "ad_group_ad.ad.responsive_search_ad.descriptions, " +
      "ad_group_ad.ad.responsive_search_ad.path1, " +
      "ad_group_ad.ad.responsive_search_ad.path2, " +
      "metrics.impressions, " +
      "metrics.clicks, " +
      "metrics.ctr, " +
      "metrics.cost_micros, " +
      "metrics.conversions, " +
      "metrics.conversions_value " +
    "FROM ad_group_ad " +
    "WHERE segments.date BETWEEN '" + CONFIG.DATE_START + "' AND '" + CONFIG.DATE_END + "' " +
      "AND ad_group_ad.ad.type IN ('RESPONSIVE_SEARCH_AD', 'EXPANDED_TEXT_AD') " +
    "ORDER BY metrics.cost_micros DESC";

  var rows = [];
  var report = AdsApp.report(rsaQuery);
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

    // Parse headlines and descriptions from RSA format
    var headlines = parseAssetList(row['ad_group_ad.ad.responsive_search_ad.headlines'] || '');
    var descriptions = parseAssetList(row['ad_group_ad.ad.responsive_search_ad.descriptions'] || '');

    var finalUrls = row['ad_group_ad.ad.final_urls'] || '';
    if (finalUrls && finalUrls !== '--') {
      if (Array.isArray(finalUrls)) {
        finalUrls = finalUrls.join(', ');
      } else {
        finalUrls = String(finalUrls).replace(/[\[\]"]/g, '');
      }
    }

    rows.push([
      row['campaign.name'],
      row['campaign.id'],
      row['ad_group.name'],
      row['ad_group.id'],
      row['ad_group_ad.ad.id'],
      row['ad_group_ad.ad.type'],
      row['ad_group_ad.status'],
      finalUrls,
      headlines[0] || '',
      headlines[1] || '',
      headlines[2] || '',
      descriptions[0] || '',
      descriptions[1] || '',
      row['ad_group_ad.ad.responsive_search_ad.path1'] || '',
      row['ad_group_ad.ad.responsive_search_ad.path2'] || '',
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
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }

  Logger.log('Ad Copy Performance: ' + rows.length + ' ads exported.');
}

/**
 * Parse Google Ads asset list format into an array of text values.
 * RSA headlines/descriptions come as JSON-like arrays of objects.
 */
function parseAssetList(assets) {
  if (!assets || assets === '--') {
    return [];
  }

  var texts = [];

  // Google Ads may return an array of objects with .text property
  if (Array.isArray(assets)) {
    for (var i = 0; i < assets.length; i++) {
      var item = assets[i];
      if (item && typeof item === 'object' && item.text) {
        texts.push(item.text);
      } else if (item && typeof item === 'object' && item.asset_text) {
        texts.push(item.asset_text);
      } else if (typeof item === 'string') {
        texts.push(item);
      }
    }
    return texts;
  }

  // If it's a string, try to parse it
  var assetStr = String(assets);
  if (assetStr === '[]') {
    return [];
  }

  // Try JSON parse first
  try {
    var parsed = JSON.parse(assetStr);
    if (Array.isArray(parsed)) {
      for (var j = 0; j < parsed.length; j++) {
        if (parsed[j] && parsed[j].text) {
          texts.push(parsed[j].text);
        }
      }
      return texts;
    }
  } catch (e) {
    // Not valid JSON, try regex
  }

  // Regex fallback for stringified format
  var matches = assetStr.match(/"text"\s*:\s*"([^"]+)"/g);
  if (matches) {
    for (var k = 0; k < matches.length; k++) {
      var text = matches[k].replace(/"text"\s*:\s*"/, '').replace(/"$/, '');
      texts.push(text);
    }
  }

  return texts;
}

// ===================== HELPERS =====================
function getOrCreateSheet(ss, name) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
