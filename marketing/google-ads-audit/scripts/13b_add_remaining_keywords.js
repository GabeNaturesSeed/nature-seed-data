/**
 * Google Ads Script: Add Remaining High-Value Keywords (13b — Fix)
 * ================================================================
 *
 * FIX: Script 13 skipped 3 keywords because their ad groups weren't found.
 * Root cause: the original script filtered for ENABLED ad groups only.
 * Some ad groups (likely Hay Seed, Regional/Lawn, or All Pasture) may be
 * PAUSED in the account.
 *
 * THIS SCRIPT:
 * 1. Fetches ALL ad groups in the campaign (enabled + paused + removed)
 * 2. Logs every ad group it finds (for debugging)
 * 3. Uses case-insensitive matching
 * 4. Only adds keywords that don't already exist (safe to re-run)
 * 5. If an ad group is PAUSED, it still adds the keyword (keyword will
 *    start serving when you enable the ad group)
 *
 * TARGET: Search | Pasture | Exact (Campaign ID: 22866516659)
 *
 * INSTRUCTIONS:
 * 1. Run with DRY_RUN = true to see which ad groups exist and what will be added
 * 2. Review the "AD GROUP INVENTORY" section in the logs
 * 3. Set DRY_RUN = false to add keywords
 *
 * AUTHOR: Nature's Seed Data Orchestrator
 * DATE: 2026-03-05
 */

var DRY_RUN = true; // Set to false to add keywords

var TARGET_CAMPAIGN_ID = 22866516659;

// All 9 keywords — the script will skip ones that already exist
var KEYWORDS_TO_ADD = [
  { ad_group: 'All Pasture',    text: 'pasture seed',            match_type: 'PHRASE', formatted: '"pasture seed"',             hist_revenue: 24102, hist_roas: 3.15 },
  { ad_group: 'All Pasture',    text: 'pasture seed',            match_type: 'EXACT',  formatted: '[pasture seed]',             hist_revenue: 15331, hist_roas: 3.65 },
  { ad_group: 'All Pasture',    text: 'pasture grass mix',       match_type: 'PHRASE', formatted: '"pasture grass mix"',        hist_revenue: 7576,  hist_roas: 3.44 },
  { ad_group: 'Hay Seed',       text: 'hay seed mix',            match_type: 'BROAD',  formatted: 'hay seed mix',              hist_revenue: 11127, hist_roas: 10.75 },
  { ad_group: 'Regional/Lawn',  text: 'lawn seed',               match_type: 'PHRASE', formatted: '"lawn seed"',               hist_revenue: 7354,  hist_roas: 3.61 },
  { ad_group: 'Horse',          text: 'horse pasture seed',      match_type: 'PHRASE', formatted: '"horse pasture seed"',       hist_revenue: 9695,  hist_roas: 3.75 },
  { ad_group: 'Sheep',          text: 'sheep pasture mix',       match_type: 'PHRASE', formatted: '"sheep pasture mix"',        hist_revenue: 5514,  hist_roas: 9.51 },
  { ad_group: 'Cattle',         text: 'best cattle pasture mix', match_type: 'PHRASE', formatted: '"best cattle pasture mix"',  hist_revenue: 5391,  hist_roas: 12.78 },
  { ad_group: 'Cattle',         text: 'cattle pasture seed',     match_type: 'EXACT',  formatted: '[cattle pasture seed]',      hist_revenue: 5165,  hist_roas: 11.18 }
];


function main() {
  Logger.log('================================================================');
  Logger.log('Add Remaining High-Value Keywords (13b Fix)');
  Logger.log('Mode: ' + (DRY_RUN ? 'DRY RUN' : 'LIVE'));
  Logger.log('================================================================\n');

  // --- Get campaign ---
  var campaignIterator = AdsApp.campaigns()
    .withCondition('CampaignId = ' + TARGET_CAMPAIGN_ID)
    .get();

  if (!campaignIterator.hasNext()) {
    Logger.log('ERROR: Campaign ' + TARGET_CAMPAIGN_ID + ' not found. Trying without status filter...');
    // Try GAQL which can find paused campaigns too
    var query = "SELECT campaign.name, campaign.status FROM campaign WHERE campaign.id = " + TARGET_CAMPAIGN_ID;
    var results = AdsApp.search(query);
    if (results.hasNext()) {
      var row = results.next();
      Logger.log('Campaign found via GAQL: ' + row.campaign.name + ' (status: ' + row.campaign.status + ')');
      Logger.log('Campaign is not ENABLED — keywords can still be added but won\'t serve until campaign is enabled.');
    } else {
      Logger.log('Campaign truly not found. Exiting.');
      return;
    }
  }

  // --- Get ALL ad groups (no status filter) using GAQL ---
  Logger.log('--- AD GROUP INVENTORY (all statuses) ---\n');

  var agQuery = 'SELECT ad_group.name, ad_group.id, ad_group.status ' +
    'FROM ad_group ' +
    'WHERE campaign.id = ' + TARGET_CAMPAIGN_ID + ' ' +
    'ORDER BY ad_group.name ASC';

  var agReport = AdsApp.search(agQuery);
  var adGroupMap = {};        // normalized name → { name, id, status }
  var adGroupOriginal = {};   // normalized name → original name

  while (agReport.hasNext()) {
    var agRow = agReport.next();
    var agName = agRow.adGroup.name;
    var agId = agRow.adGroup.id;
    var agStatus = agRow.adGroup.status;
    var normalized = agName.trim().toLowerCase();

    adGroupMap[normalized] = { name: agName, id: agId, status: agStatus };
    adGroupOriginal[normalized] = agName;

    var statusFlag = (agStatus === 'ENABLED') ? '' : ' ← ' + agStatus;
    Logger.log('  ' + agName + ' (ID: ' + agId + ')' + statusFlag);
  }

  var totalAGs = Object.keys(adGroupMap).length;
  Logger.log('\nTotal ad groups found: ' + totalAGs);
  Logger.log('');

  // --- Get existing keywords (all statuses) ---
  var existingKeywords = {};
  var kwQuery = 'SELECT ad_group.name, ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type ' +
    'FROM keyword_view ' +
    'WHERE campaign.id = ' + TARGET_CAMPAIGN_ID;

  try {
    var kwReport = AdsApp.search(kwQuery);
    while (kwReport.hasNext()) {
      var kwRow = kwReport.next();
      var key = kwRow.adGroup.name.trim().toLowerCase() + '|' +
                kwRow.adGroupCriterion.keyword.text.toLowerCase() + '|' +
                kwRow.adGroupCriterion.keyword.matchType;
      existingKeywords[key] = true;
    }
  } catch (e) {
    Logger.log('WARNING: Could not fetch existing keywords via GAQL: ' + e.message);
    Logger.log('Duplicate check will use AdsApp iterator instead.\n');

    var kwIterator = AdsApp.keywords()
      .withCondition('CampaignId = ' + TARGET_CAMPAIGN_ID)
      .get();
    while (kwIterator.hasNext()) {
      var kw = kwIterator.next();
      var key = kw.getAdGroup().getName().trim().toLowerCase() + '|' +
                kw.getText().toLowerCase() + '|' +
                kw.getMatchType();
      existingKeywords[key] = true;
    }
  }

  Logger.log('Existing keywords in campaign: ' + Object.keys(existingKeywords).length + '\n');

  // --- Process keywords ---
  Logger.log('--- PROCESSING KEYWORDS ---\n');

  var stats = { added: 0, skipped_exists: 0, skipped_no_ag: 0, failed: 0, paused_ag: 0 };

  for (var i = 0; i < KEYWORDS_TO_ADD.length; i++) {
    var kwDef = KEYWORDS_TO_ADD[i];
    var normalizedAG = kwDef.ad_group.trim().toLowerCase();

    // Look up ad group (case-insensitive)
    var agInfo = adGroupMap[normalizedAG];

    if (!agInfo) {
      // Try fuzzy match — look for ad groups containing our target name
      var fuzzyMatch = null;
      for (var agKey in adGroupMap) {
        if (agKey.indexOf(normalizedAG) !== -1 || normalizedAG.indexOf(agKey) !== -1) {
          fuzzyMatch = adGroupMap[agKey];
          break;
        }
      }

      if (fuzzyMatch) {
        Logger.log('⚠ FUZZY MATCH: "' + kwDef.ad_group + '" → matched to "' + fuzzyMatch.name + '"');
        agInfo = fuzzyMatch;
      } else {
        Logger.log('✗ AD GROUP NOT FOUND: "' + kwDef.ad_group + '"');
        Logger.log('    Keyword: ' + kwDef.formatted);
        Logger.log('    Available ad groups: ' + Object.keys(adGroupOriginal).map(function(k) { return adGroupOriginal[k]; }).join(', '));
        Logger.log('    → You need to create this ad group manually.\n');
        stats.skipped_no_ag++;
        continue;
      }
    }

    // Log if ad group is paused
    if (agInfo.status !== 'ENABLED') {
      Logger.log('ℹ Ad group "' + agInfo.name + '" is ' + agInfo.status + ' — keyword will be added but won\'t serve until ad group is enabled.');
      stats.paused_ag++;
    }

    // Check for duplicates
    var dupeKey = agInfo.name.trim().toLowerCase() + '|' + kwDef.text.toLowerCase() + '|' + kwDef.match_type;
    if (existingKeywords[dupeKey]) {
      Logger.log('  SKIP (already exists): ' + kwDef.formatted + ' in ' + agInfo.name + '\n');
      stats.skipped_exists++;
      continue;
    }

    // Add keyword
    if (DRY_RUN) {
      Logger.log('[DRY RUN] WOULD ADD:');
    } else {
      Logger.log('ADDING:');
    }
    Logger.log('    Ad Group:     ' + agInfo.name + ' (' + agInfo.status + ')');
    Logger.log('    Keyword:      ' + kwDef.formatted);
    Logger.log('    Hist Revenue: $' + kwDef.hist_revenue.toLocaleString());
    Logger.log('    Hist ROAS:    ' + kwDef.hist_roas + 'x\n');

    if (!DRY_RUN) {
      try {
        // Get the ad group object via iterator (works for enabled + paused)
        var adGroupIterator = AdsApp.adGroups()
          .withCondition('CampaignId = ' + TARGET_CAMPAIGN_ID)
          .withIds([agInfo.id])
          .get();

        if (!adGroupIterator.hasNext()) {
          // Fallback: try by name
          adGroupIterator = AdsApp.adGroups()
            .withCondition('CampaignId = ' + TARGET_CAMPAIGN_ID)
            .withCondition('Name = "' + agInfo.name.replace(/"/g, '\\"') + '"')
            .get();
        }

        if (adGroupIterator.hasNext()) {
          var adGroup = adGroupIterator.next();
          var result = adGroup.newKeywordBuilder()
            .withText(kwDef.formatted)
            .build();

          if (result.isSuccessful()) {
            stats.added++;
            Logger.log('    ✓ Added successfully.\n');
          } else {
            stats.failed++;
            var errors = result.getErrors();
            Logger.log('    ✗ Build failed: ' + (errors.length > 0 ? errors.join(', ') : 'Unknown') + '\n');
          }
        } else {
          stats.failed++;
          Logger.log('    ✗ Could not get ad group object for ID ' + agInfo.id + '\n');
        }
      } catch (e) {
        stats.failed++;
        Logger.log('    ✗ Exception: ' + e.message + '\n');
      }
    }
  }

  // --- Summary ---
  Logger.log('================================================================');
  Logger.log('SUMMARY');
  Logger.log('================================================================');
  Logger.log('Keywords targeted:       ' + KEYWORDS_TO_ADD.length);
  Logger.log('Added:                   ' + stats.added);
  Logger.log('Skipped (already exist): ' + stats.skipped_exists);
  Logger.log('Skipped (no ad group):   ' + stats.skipped_no_ag);
  Logger.log('Failed:                  ' + stats.failed);
  Logger.log('In paused ad groups:     ' + stats.paused_ag);

  if (stats.paused_ag > 0) {
    Logger.log('\n⚠ Some keywords were added to PAUSED ad groups.');
    Logger.log('  They won\'t serve traffic until you ENABLE those ad groups.');
    Logger.log('  Go to the campaign → Ad Groups → find the paused ones → Enable.');
  }

  if (DRY_RUN) {
    Logger.log('\n*** DRY RUN COMPLETE. Set DRY_RUN = false to add keywords. ***');
  } else if (stats.added > 0) {
    Logger.log('\n*** DONE. ' + stats.added + ' keywords added. ***');
  }
}
