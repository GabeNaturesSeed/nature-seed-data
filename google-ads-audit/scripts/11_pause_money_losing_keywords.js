/**
 * Google Ads Script: Pause Money-Losing Keywords (1.2 Option A + 1.3)
 * ====================================================================
 *
 * PURPOSE:
 * Pauses all 24 enabled keywords that have ROAS < 1.0x in the last 3 months.
 * These keywords spent $2,300+ and returned less than $1 for every $1 spent.
 *
 * SCOPE:
 * - Search | Animal Seed (Broad) | ROAS  (Campaign ID: 22999216985) — 12 keywords
 * - Search | Pasture | Exact             (Campaign ID: 22866516659) — 12 keywords
 * - ONLY touches keywords in ENABLED campaigns with ENABLED status
 *
 * THE 6 WORST (1.2 Option A) are marked with ★ in the logs:
 *   horse pasture seed mix ($949, 0.65x), sheep forage seed mix ($338, 0.20x),
 *   best perennial wildflower seed mix ($189, 0.92x), chicken pasture seed ($124, 0.56x),
 *   forage seed mix for chickens ($95, 0.21x), alpaca pasture seed ($87, 0.21x)
 *
 * INSTRUCTIONS:
 * 1. Paste into Google Ads → Tools → Scripts
 * 2. Run with DRY_RUN = true (default) to preview
 * 3. Review logs carefully
 * 4. Set DRY_RUN = false and run again to pause
 *
 * AUTHOR: Nature's Seed Data Orchestrator
 * DATE: 2026-03-05
 * SOURCE: LIVE_STATE_AUDIT.md Section 5, LIVE_top_keywords.csv
 */

var DRY_RUN = true; // Set to false to actually pause keywords

// ============================================================
// KEYWORDS TO PAUSE
// ============================================================
// Format: { campaign_id, ad_group, text, match_type, spend_3m, roas_3m, is_top6 }
// Source: LIVE_top_keywords.csv — all entries with status "MONEY LOSER"

var KEYWORDS_TO_PAUSE = [

  // =====================================================
  // Campaign: Search | Animal Seed (Broad) | ROAS
  // Campaign ID: 22999216985
  // =====================================================

  // ★ TOP 6 WORST (1.2 Option A)
  { campaign_id: 22999216985, ad_group: 'Horse',          text: 'horse pasture seed mix',          match_type: 'BROAD', spend: 949,  roas: 0.65, top6: true },
  { campaign_id: 22999216985, ad_group: 'Sheep',          text: 'sheep forage seed mix',            match_type: 'BROAD', spend: 338,  roas: 0.20, top6: true },
  { campaign_id: 22999216985, ad_group: 'Wildflower Seed',text: 'best perennial wildflower seed mix',match_type: 'BROAD', spend: 189, roas: 0.92, top6: true },
  { campaign_id: 22999216985, ad_group: 'Poultry',        text: 'chicken pasture seed',             match_type: 'BROAD', spend: 124,  roas: 0.56, top6: true },
  { campaign_id: 22999216985, ad_group: 'Poultry',        text: 'forage seed mix for chickens',     match_type: 'BROAD', spend: 95,   roas: 0.21, top6: true },
  { campaign_id: 22999216985, ad_group: 'Alpaca',         text: 'alpaca pasture seed',              match_type: 'BROAD', spend: 87,   roas: 0.21, top6: true },

  // Remaining 6 in Animal Seed (Broad)
  { campaign_id: 22999216985, ad_group: 'Wildflower Seed',text: 'arizona wildflower seed mix',      match_type: 'BROAD', spend: 32,   roas: 0.00, top6: false },
  { campaign_id: 22999216985, ad_group: 'Microclover',    text: 'bulk micro clover seed',           match_type: 'BROAD', spend: 31,   roas: 0.00, top6: false },
  { campaign_id: 22999216985, ad_group: 'Pig',            text: 'pig pasture seed',                 match_type: 'BROAD', spend: 25,   roas: 0.00, top6: false },
  { campaign_id: 22999216985, ad_group: 'White Clover',   text: 'white clover grass seed',          match_type: 'BROAD', spend: 24,   roas: 0.00, top6: false },
  { campaign_id: 22999216985, ad_group: 'White Clover',   text: 'white clover lawn',                match_type: 'BROAD', spend: 22,   roas: 0.00, top6: false },
  { campaign_id: 22999216985, ad_group: 'White Clover',   text: 'white clover grass',               match_type: 'BROAD', spend: 21,   roas: 0.00, top6: false },

  // =====================================================
  // Campaign: Search | Pasture | Exact
  // Campaign ID: 22866516659
  // =====================================================

  { campaign_id: 22866516659, ad_group: 'Sheep',      text: 'pasture grass for sheep',              match_type: 'EXACT',  spend: 134, roas: 0.01, top6: false },
  { campaign_id: 22866516659, ad_group: 'Wildflowers', text: 'wildflower seeds',                    match_type: 'PHRASE', spend: 121, roas: 0.00, top6: false },
  { campaign_id: 22866516659, ad_group: 'Cattle',      text: 'pasture grass seed mix',              match_type: 'PHRASE', spend: 112, roas: 0.44, top6: false },
  { campaign_id: 22866516659, ad_group: 'Poultry',     text: 'chicken safe grass seed',             match_type: 'PHRASE', spend: 27,  roas: 0.00, top6: false },
  { campaign_id: 22866516659, ad_group: 'Llama',       text: 'alpaca grass seed',                   match_type: 'PHRASE', spend: 25,  roas: 0.00, top6: false },
  { campaign_id: 22866516659, ad_group: 'Horse',       text: 'pasture grass seed for horses',       match_type: 'PHRASE', spend: 24,  roas: 0.00, top6: false },
  { campaign_id: 22866516659, ad_group: 'Hay Seed',    text: 'timothy grass seed',                  match_type: 'PHRASE', spend: 21,  roas: 0.00, top6: false },
  { campaign_id: 22866516659, ad_group: 'Horse',       text: 'pasture seed for horses',             match_type: 'PHRASE', spend: 19,  roas: 0.00, top6: false },
  { campaign_id: 22866516659, ad_group: 'Sheep',       text: 'pasture grass for sheep',             match_type: 'PHRASE', spend: 41,  roas: 0.00, top6: false },
  { campaign_id: 22866516659, ad_group: 'Sheep',       text: 'sheep forage seed mix',               match_type: 'EXACT',  spend: 37,  roas: 0.00, top6: false },
  { campaign_id: 22866516659, ad_group: 'Wildflowers', text: 'california wildflower seeds',         match_type: 'PHRASE', spend: 14,  roas: 0.00, top6: false },
  { campaign_id: 22866516659, ad_group: 'Wildflowers', text: 'california native wildflower seeds',  match_type: 'PHRASE', spend: 11,  roas: 0.00, top6: false }
];


// ============================================================
// MAIN
// ============================================================

function main() {
  Logger.log('================================================================');
  Logger.log('Pause Money-Losing Keywords');
  Logger.log('Mode: ' + (DRY_RUN ? 'DRY RUN (preview)' : 'LIVE (pausing keywords)'));
  Logger.log('Keywords to pause: ' + KEYWORDS_TO_PAUSE.length);
  Logger.log('  - Top 6 worst (1.2 Option A): ' + KEYWORDS_TO_PAUSE.filter(function(k){ return k.top6; }).length);
  Logger.log('  - Additional losers (1.3):     ' + KEYWORDS_TO_PAUSE.filter(function(k){ return !k.top6; }).length);
  Logger.log('================================================================\n');

  // Fetch all enabled keywords from the two target campaigns
  var targetCampaignIds = [22999216985, 22866516659];

  var keywordIterator = AdsApp.keywords()
    .withCondition('CampaignId IN [' + targetCampaignIds.join(',') + ']')
    .withCondition('Status = ENABLED')
    .get();

  // Build lookup of live keywords: key = "campaignId|adGroup|text|matchType"
  var liveKeywords = {};
  var totalLive = 0;

  while (keywordIterator.hasNext()) {
    var kw = keywordIterator.next();
    totalLive++;

    var key = kw.getCampaign().getId() + '|' +
              kw.getAdGroup().getName() + '|' +
              kw.getText().toLowerCase() + '|' +
              kw.getMatchType();

    liveKeywords[key] = kw;
  }

  Logger.log('Found ' + totalLive + ' enabled keywords in target campaigns.\n');

  // Match and pause
  var stats = { matched: 0, paused: 0, notFound: 0, failed: 0 };

  for (var i = 0; i < KEYWORDS_TO_PAUSE.length; i++) {
    var target = KEYWORDS_TO_PAUSE[i];
    var key = target.campaign_id + '|' +
              target.ad_group + '|' +
              target.text.toLowerCase() + '|' +
              target.match_type;

    var kw = liveKeywords[key];

    var label = target.top6 ? '★ TOP 6' : '  LOSER';

    if (kw) {
      stats.matched++;

      var prefix = DRY_RUN ? '[DRY RUN] WOULD PAUSE' : 'PAUSING';
      Logger.log(label + ' | ' + prefix +
        '\n    Campaign: ' + kw.getCampaign().getName() +
        '\n    Ad Group: ' + target.ad_group +
        '\n    Keyword:  ' + target.text +
        '\n    Match:    ' + target.match_type +
        '\n    3M Spend: $' + target.spend + ' | 3M ROAS: ' + target.roas + 'x\n');

      if (!DRY_RUN) {
        try {
          kw.pause();
          stats.paused++;
        } catch (e) {
          stats.failed++;
          Logger.log('    ERROR: ' + e.message + '\n');
        }
      }
    } else {
      stats.notFound++;
      Logger.log(label + ' | NOT FOUND (may already be paused)' +
        '\n    Ad Group: ' + target.ad_group +
        '\n    Keyword:  ' + target.text +
        '\n    Match:    ' + target.match_type + '\n');
    }
  }

  // Summary
  Logger.log('================================================================');
  Logger.log('SUMMARY');
  Logger.log('================================================================');
  Logger.log('Keywords targeted:  ' + KEYWORDS_TO_PAUSE.length);
  Logger.log('Found & matched:    ' + stats.matched);
  Logger.log('Paused:             ' + stats.paused);
  Logger.log('Not found:          ' + stats.notFound);
  Logger.log('Failed:             ' + stats.failed);
  Logger.log('');

  var totalSaved = 0;
  for (var j = 0; j < KEYWORDS_TO_PAUSE.length; j++) {
    totalSaved += KEYWORDS_TO_PAUSE[j].spend;
  }
  Logger.log('Estimated 3-month savings: $' + totalSaved);
  Logger.log('Estimated monthly savings: ~$' + Math.round(totalSaved / 3));

  if (DRY_RUN && stats.matched > 0) {
    Logger.log('\n*** DRY RUN COMPLETE. Set DRY_RUN = false to pause these keywords. ***');
  } else if (!DRY_RUN && stats.paused > 0) {
    Logger.log('\n*** DONE. ' + stats.paused + ' keywords paused. ***');
    Logger.log('*** To undo: filter for paused keywords in these campaigns and re-enable. ***');
  }
}
