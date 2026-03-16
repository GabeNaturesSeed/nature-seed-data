/**
 * Google Ads Script: Add Missing High-Value Keywords (2.2)
 * ========================================================
 *
 * PURPOSE:
 * Adds historically proven keywords that are NOT in any current campaign.
 * These keywords drove $100K+ combined revenue at 3-12x ROAS in the past
 * but were lost when old campaigns were paused/removed.
 *
 * TARGET CAMPAIGN:
 * Search | Pasture | Exact (Campaign ID: 22866516659)
 * Keywords are added to EXISTING ad groups within this campaign.
 *
 * KEYWORDS BEING ADDED (9 total):
 *
 * | Keyword              | Match  | Ad Group      | Hist Revenue | Hist ROAS |
 * |----------------------|--------|---------------|-------------|-----------|
 * | pasture seed         | PHRASE | All Pasture   | $24,102     | 3.15x     |
 * | pasture seed         | EXACT  | All Pasture   | $15,331     | 3.65x     |
 * | pasture grass mix    | PHRASE | All Pasture   | $7,576      | 3.44x     |
 * | hay seed mix         | BROAD  | Hay Seed      | $11,127     | 10.75x    |
 * | lawn seed            | PHRASE | Regional/Lawn | $7,354      | 3.61x     |
 * | horse pasture seed   | PHRASE | Horse         | $9,695      | 3.75x     |
 * | sheep pasture mix    | PHRASE | Sheep         | $5,514      | 9.51x     |
 * | best cattle pasture mix | PHRASE | Cattle     | $5,391      | 12.78x    |
 * | cattle pasture seed  | EXACT  | Cattle        | $5,165      | 11.18x    |
 *
 * INSTRUCTIONS:
 * 1. Paste into Google Ads → Tools → Scripts
 * 2. Run with DRY_RUN = true to preview
 * 3. Verify the ad groups exist and keywords don't already exist
 * 4. Set DRY_RUN = false and run to add keywords
 *
 * IMPORTANT:
 * - No CPC bids are set — keywords inherit the campaign's Smart Bidding strategy
 *   (currently Maximize Conversions; recommendation: switch to Maximize Conv Value)
 * - New keywords start paused by default in some accounts; check after running
 *
 * AUTHOR: Nature's Seed Data Orchestrator
 * DATE: 2026-03-05
 * SOURCE: LIVE_STATE_AUDIT.md Section 10 (Gap Analysis — Keyword Gaps)
 */

var DRY_RUN = true; // Set to false to add keywords

// ============================================================
// TARGET CAMPAIGN
// ============================================================

var TARGET_CAMPAIGN_ID = 22866516659; // Search | Pasture | Exact

// ============================================================
// KEYWORDS TO ADD
// ============================================================
// Format: { ad_group, text, match_type, hist_revenue, hist_roas }
//
// Google Ads keyword text format:
//   BROAD:  keyword text
//   PHRASE: "keyword text"
//   EXACT:  [keyword text]

var KEYWORDS_TO_ADD = [
  // --- All Pasture ad group ---
  // "pasture seed" was the #1 keyword family historically — $39K+ combined revenue
  {
    ad_group: 'All Pasture',
    text: 'pasture seed',
    match_type: 'PHRASE',
    formatted: '"pasture seed"',
    hist_revenue: 24102,
    hist_roas: 3.15,
    note: '#1 missing keyword — drove $24K revenue at 3.15x from Categories (Top) campaign'
  },
  {
    ad_group: 'All Pasture',
    text: 'pasture seed',
    match_type: 'EXACT',
    formatted: '[pasture seed]',
    hist_revenue: 15331,
    hist_roas: 3.65,
    note: 'Exact match complement — $15K revenue at 3.65x'
  },
  {
    ad_group: 'All Pasture',
    text: 'pasture grass mix',
    match_type: 'PHRASE',
    formatted: '"pasture grass mix"',
    hist_revenue: 7576,
    hist_roas: 3.44,
    note: '$7.5K revenue at 3.44x from Pasture Seed (Broad) campaign'
  },

  // --- Hay Seed ad group ---
  // Best ROAS of any missing keyword: 10.75x
  {
    ad_group: 'Hay Seed',
    text: 'hay seed mix',
    match_type: 'BROAD',
    formatted: 'hay seed mix',
    hist_revenue: 11127,
    hist_roas: 10.75,
    note: 'EXCEPTIONAL — 10.75x ROAS, $11K revenue, zero current coverage'
  },

  // --- Regional/Lawn ad group ---
  // No lawn seed keyword exists anywhere in the account
  {
    ad_group: 'Regional/Lawn',
    text: 'lawn seed',
    match_type: 'PHRASE',
    formatted: '"lawn seed"',
    hist_revenue: 7354,
    hist_roas: 3.61,
    note: 'MAJOR GAP — $7.3K revenue, zero current lawn seed search coverage'
  },

  // --- Horse ad group ---
  {
    ad_group: 'Horse',
    text: 'horse pasture seed',
    match_type: 'PHRASE',
    formatted: '"horse pasture seed"',
    hist_revenue: 9695,
    hist_roas: 3.75,
    note: '$9.7K revenue at 3.75x — the broad match version is being paused, this phrase version is tighter'
  },

  // --- Sheep ad group ---
  {
    ad_group: 'Sheep',
    text: 'sheep pasture mix',
    match_type: 'PHRASE',
    formatted: '"sheep pasture mix"',
    hist_revenue: 5514,
    hist_roas: 9.51,
    note: '9.51x ROAS — high-intent buyer query'
  },

  // --- Cattle ad group ---
  {
    ad_group: 'Cattle',
    text: 'best cattle pasture mix',
    match_type: 'PHRASE',
    formatted: '"best cattle pasture mix"',
    hist_revenue: 5391,
    hist_roas: 12.78,
    note: '12.78x ROAS — extremely high-intent, "best" modifier signals buyer'
  },
  {
    ad_group: 'Cattle',
    text: 'cattle pasture seed',
    match_type: 'EXACT',
    formatted: '[cattle pasture seed]',
    hist_revenue: 5165,
    hist_roas: 11.18,
    note: '11.18x ROAS — proven exact match performer'
  }
];


// ============================================================
// MAIN
// ============================================================

function main() {
  Logger.log('================================================================');
  Logger.log('Add Missing High-Value Keywords');
  Logger.log('Mode: ' + (DRY_RUN ? 'DRY RUN (preview)' : 'LIVE (adding keywords)'));
  Logger.log('Target campaign: Search | Pasture | Exact (ID: ' + TARGET_CAMPAIGN_ID + ')');
  Logger.log('Keywords to add: ' + KEYWORDS_TO_ADD.length);
  Logger.log('Combined historical revenue: $' + KEYWORDS_TO_ADD.reduce(function(s, k) { return s + k.hist_revenue; }, 0).toLocaleString());
  Logger.log('================================================================\n');

  // Fetch the target campaign
  var campaignIterator = AdsApp.campaigns()
    .withCondition('CampaignId = ' + TARGET_CAMPAIGN_ID)
    .withCondition('Status = ENABLED')
    .get();

  if (!campaignIterator.hasNext()) {
    Logger.log('ERROR: Campaign ID ' + TARGET_CAMPAIGN_ID + ' not found or not enabled.');
    return;
  }

  var campaign = campaignIterator.next();
  Logger.log('Campaign found: ' + campaign.getName() + '\n');

  // Build ad group lookup
  var adGroups = {};
  var agIterator = campaign.adGroups().withCondition('Status = ENABLED').get();
  while (agIterator.hasNext()) {
    var ag = agIterator.next();
    adGroups[ag.getName()] = ag;
  }

  Logger.log('Ad groups in campaign: ' + Object.keys(adGroups).join(', ') + '\n');

  // Build existing keyword lookup to check for duplicates
  var existingKeywords = {};
  var kwIterator = AdsApp.keywords()
    .withCondition('CampaignId = ' + TARGET_CAMPAIGN_ID)
    .get();

  while (kwIterator.hasNext()) {
    var kw = kwIterator.next();
    var key = kw.getAdGroup().getName() + '|' + kw.getText().toLowerCase() + '|' + kw.getMatchType();
    existingKeywords[key] = true;
  }

  Logger.log('Existing keywords in campaign: ' + Object.keys(existingKeywords).length + '\n');
  Logger.log('--- Processing keywords ---\n');

  var stats = { added: 0, skipped_exists: 0, skipped_no_ag: 0, failed: 0 };

  for (var i = 0; i < KEYWORDS_TO_ADD.length; i++) {
    var kwDef = KEYWORDS_TO_ADD[i];
    var adGroup = adGroups[kwDef.ad_group];

    // Check ad group exists
    if (!adGroup) {
      Logger.log('⚠ SKIP — Ad group "' + kwDef.ad_group + '" not found in campaign');
      Logger.log('    Keyword: ' + kwDef.formatted);
      Logger.log('    Fix: Create this ad group manually, then re-run.\n');
      stats.skipped_no_ag++;
      continue;
    }

    // Check for duplicates
    var dupeKey = kwDef.ad_group + '|' + kwDef.text.toLowerCase() + '|' + kwDef.match_type;
    if (existingKeywords[dupeKey]) {
      Logger.log('  SKIP (already exists): ' + kwDef.formatted + ' in ' + kwDef.ad_group);
      stats.skipped_exists++;
      continue;
    }

    // Add keyword
    if (DRY_RUN) {
      Logger.log('[DRY RUN] WOULD ADD:');
    } else {
      Logger.log('ADDING:');
    }
    Logger.log('    Ad Group:     ' + kwDef.ad_group);
    Logger.log('    Keyword:      ' + kwDef.formatted);
    Logger.log('    Match Type:   ' + kwDef.match_type);
    Logger.log('    Hist Revenue: $' + kwDef.hist_revenue.toLocaleString());
    Logger.log('    Hist ROAS:    ' + kwDef.hist_roas + 'x');
    Logger.log('    Note:         ' + kwDef.note);
    Logger.log('');

    if (!DRY_RUN) {
      try {
        var result = adGroup.newKeywordBuilder()
          .withText(kwDef.formatted)
          .build();

        if (result.isSuccessful()) {
          stats.added++;
          Logger.log('    ✓ Successfully added.\n');
        } else {
          stats.failed++;
          var errors = result.getErrors();
          Logger.log('    ✗ Failed: ' + (errors.length > 0 ? errors.join(', ') : 'Unknown error') + '\n');
        }
      } catch (e) {
        stats.failed++;
        Logger.log('    ✗ Exception: ' + e.message + '\n');
      }
    }
  }

  // Summary
  Logger.log('================================================================');
  Logger.log('SUMMARY');
  Logger.log('================================================================');
  Logger.log('Keywords targeted:       ' + KEYWORDS_TO_ADD.length);
  Logger.log('Added:                   ' + stats.added);
  Logger.log('Skipped (already exist): ' + stats.skipped_exists);
  Logger.log('Skipped (no ad group):   ' + stats.skipped_no_ag);
  Logger.log('Failed:                  ' + stats.failed);
  Logger.log('');

  if (DRY_RUN) {
    Logger.log('*** DRY RUN COMPLETE. Set DRY_RUN = false to add keywords. ***');
  } else if (stats.added > 0) {
    Logger.log('*** DONE. ' + stats.added + ' keywords added. ***');
    Logger.log('');
    Logger.log('NEXT STEPS:');
    Logger.log('1. Check that new keywords are ENABLED (not auto-paused)');
    Logger.log('2. Consider changing campaign bidding to "Maximize Conversion Value"');
    Logger.log('   (currently on "Maximize Conversions" which optimizes for count, not revenue)');
    Logger.log('3. Monitor these keywords for 2-4 weeks before adjusting');
    Logger.log('4. Consider increasing campaign budget from $78 to $148/day');
    Logger.log('   to accommodate the new keyword traffic');
  }
}
