/**
 * Google Ads Script: Add Negative Keywords (1.4)
 * ================================================
 *
 * PURPOSE:
 * Adds negative keywords to stop wasting money on irrelevant search terms.
 * Only includes HIGH-CONFIDENCE negatives — competitor brands, products
 * not in the live catalog, and info queries with zero purchase intent.
 *
 * SOURCE: LIVE_wasted_search_terms.csv (637 terms, $8,038 wasted in Q1 2026)
 *
 * STRUCTURE:
 * - ACCOUNT-WIDE negatives → added to ALL 3 search campaigns + Shopping
 * - SHOPPING-ONLY negatives → only Shopping | Catch All.
 * - SEARCH-ONLY negatives → only the 3 Search campaigns
 *
 * CAMPAIGNS AFFECTED:
 * - Search | Brand | ROAS               (ID: 187765054)
 * - Search | Animal Seed (Broad) | ROAS (ID: 22999216985)
 * - Search | Pasture | Exact            (ID: 22866516659)
 * - Shopping | Catch All.               (matched by name)
 *
 * NOTE: PMax campaigns cannot have manual negative keywords via scripts.
 * For PMax, use account-level negative keyword lists in the UI.
 *
 * INSTRUCTIONS:
 * 1. Paste into Google Ads → Tools → Scripts
 * 2. Run with DRY_RUN = true (default) to preview
 * 3. Review logs — make sure no terms block your actual products
 * 4. Set DRY_RUN = false and run again to apply
 *
 * AUTHOR: Nature's Seed Data Orchestrator
 * DATE: 2026-03-05
 */

var DRY_RUN = true; // Set to false to apply

// ============================================================
// NEGATIVE KEYWORD DEFINITIONS
// ============================================================
// Format: [keyword_text, match_type]
// Match types: 'EXACT' → [keyword], 'PHRASE' → "keyword", 'BROAD' → keyword
//
// In createNegativeKeyword():
//   EXACT:  '[keyword text]'
//   PHRASE: '"keyword text"'
//   BROAD:  'keyword text'

// --- ACCOUNT-WIDE: Add to ALL search campaigns + Shopping ---
// Competitor brands and clearly irrelevant terms
var NEGATIVES_ALL_CAMPAIGNS = [
  // Competitor brands
  ['johnny seed', 'EXACT'],           // $44 wasted — competitor/unrelated
  ['johnny seeds', 'EXACT'],          // variant
  ["johnny's seed", 'EXACT'],         // variant
  ['granite seed', 'EXACT'],          // $41 wasted — competitor brand
  ['granite seeds', 'EXACT'],         // variant
  ['sustane', 'PHRASE'],              // $28 wasted — fertilizer brand "sustane 18 1 8"
];

// --- SHOPPING ONLY: Terms that waste Shopping budget ---
// Products not in the live catalog (280 products) or info queries
var NEGATIVES_SHOPPING_ONLY = [
  // Warm-season grasses NOT in catalog (verified against merchant feed)
  ['st augustine grass', 'PHRASE'],    // $32 wasted — not in feed
  ['st augustine seed', 'PHRASE'],
  ['zoysia grass seed', 'PHRASE'],     // $35 wasted — not in feed
  ['zoysia grass', 'PHRASE'],

  // Info / navigation queries (no purchase intent)
  ["nature's seed phone number", 'EXACT'],  // $25 wasted — info query
  ['naturesseed com', 'EXACT'],             // $44 wasted — brand nav, should go through Brand search

  // Region-specific grass NOT in their market
  ['grass seed for southern lawns', 'PHRASE'],  // $31 wasted
  ['south texas native grass seed mix', 'EXACT'], // $25 wasted
];

// --- SEARCH CAMPAIGNS ONLY: Broad/phrase match cleanup ---
// Terms that trigger Animal Seed (Broad) or Pasture Exact but are irrelevant
var NEGATIVES_SEARCH_ONLY = [
  // Informational terms
  ['phone number', 'PHRASE'],         // blocks "nature's seed phone number" from search
  ['reviews', 'PHRASE'],              // blocks review queries
  ['coupon', 'PHRASE'],               // blocks coupon queries
  ['coupon code', 'PHRASE'],

  // Off-topic animal terms
  ['dog', 'PHRASE'],                  // blocks "dog grass seed" etc.
  ['cat', 'PHRASE'],                  // blocks "cat grass seed"
  ['rabbit', 'PHRASE'],               // blocks "rabbit pasture"
];


// ============================================================
// CAMPAIGN TARGETING
// ============================================================

var SEARCH_CAMPAIGN_IDS = [187765054, 22999216985, 22866516659];
// Note: Shopping campaign found by name since Standard Shopping uses different API


// ============================================================
// MAIN
// ============================================================

function main() {
  Logger.log('================================================================');
  Logger.log('Add Negative Keywords');
  Logger.log('Mode: ' + (DRY_RUN ? 'DRY RUN (preview)' : 'LIVE (adding negatives)'));
  Logger.log('================================================================');
  Logger.log('Account-wide negatives: ' + NEGATIVES_ALL_CAMPAIGNS.length);
  Logger.log('Shopping-only negatives: ' + NEGATIVES_SHOPPING_ONLY.length);
  Logger.log('Search-only negatives: ' + NEGATIVES_SEARCH_ONLY.length);
  Logger.log('Total negative terms: ' + (NEGATIVES_ALL_CAMPAIGNS.length + NEGATIVES_SHOPPING_ONLY.length + NEGATIVES_SEARCH_ONLY.length));
  Logger.log('================================================================\n');

  var stats = { added: 0, skipped: 0, failed: 0 };

  // --- 1. Get Search campaigns ---
  var searchCampaigns = [];
  var searchIterator = AdsApp.campaigns()
    .withCondition('CampaignId IN [' + SEARCH_CAMPAIGN_IDS.join(',') + ']')
    .withCondition('Status = ENABLED')
    .get();

  while (searchIterator.hasNext()) {
    searchCampaigns.push(searchIterator.next());
  }
  Logger.log('Found ' + searchCampaigns.length + ' search campaigns.\n');

  // --- 2. Get Shopping campaign ---
  var shoppingCampaigns = [];
  var shopIterator = AdsApp.shoppingCampaigns()
    .withCondition('Status = ENABLED')
    .get();

  while (shopIterator.hasNext()) {
    var sc = shopIterator.next();
    if (sc.getName().indexOf('Catch All') !== -1) {
      shoppingCampaigns.push(sc);
    }
  }
  Logger.log('Found ' + shoppingCampaigns.length + ' shopping campaign(s).\n');

  // --- 3. Add ACCOUNT-WIDE negatives (all search + shopping) ---
  Logger.log('--- ACCOUNT-WIDE NEGATIVES ---\n');
  var allCampaigns = searchCampaigns.concat(shoppingCampaigns);

  for (var i = 0; i < NEGATIVES_ALL_CAMPAIGNS.length; i++) {
    var neg = NEGATIVES_ALL_CAMPAIGNS[i];
    var formattedKw = formatNegative(neg[0], neg[1]);

    for (var c = 0; c < allCampaigns.length; c++) {
      addNegative_(allCampaigns[c], formattedKw, neg[0], neg[1], stats);
    }
  }

  // --- 4. Add SHOPPING-ONLY negatives ---
  Logger.log('\n--- SHOPPING-ONLY NEGATIVES ---\n');

  for (var i = 0; i < NEGATIVES_SHOPPING_ONLY.length; i++) {
    var neg = NEGATIVES_SHOPPING_ONLY[i];
    var formattedKw = formatNegative(neg[0], neg[1]);

    for (var c = 0; c < shoppingCampaigns.length; c++) {
      addNegative_(shoppingCampaigns[c], formattedKw, neg[0], neg[1], stats);
    }
  }

  // --- 5. Add SEARCH-ONLY negatives ---
  Logger.log('\n--- SEARCH-ONLY NEGATIVES ---\n');

  for (var i = 0; i < NEGATIVES_SEARCH_ONLY.length; i++) {
    var neg = NEGATIVES_SEARCH_ONLY[i];
    var formattedKw = formatNegative(neg[0], neg[1]);

    for (var c = 0; c < searchCampaigns.length; c++) {
      addNegative_(searchCampaigns[c], formattedKw, neg[0], neg[1], stats);
    }
  }

  // --- Summary ---
  Logger.log('\n================================================================');
  Logger.log('SUMMARY');
  Logger.log('================================================================');
  Logger.log('Negatives added:   ' + stats.added);
  Logger.log('Already existed:   ' + stats.skipped);
  Logger.log('Failed:            ' + stats.failed);

  if (DRY_RUN) {
    Logger.log('\n*** DRY RUN COMPLETE. Set DRY_RUN = false to apply. ***');
  } else {
    Logger.log('\n*** DONE. ' + stats.added + ' negative keywords added. ***');
    Logger.log('*** To review: Campaign → Keywords → Negative Keywords tab ***');
  }
}


// ============================================================
// HELPER FUNCTIONS
// ============================================================

/**
 * Format a keyword text + match type into Google Ads negative keyword syntax.
 * EXACT: [keyword]   PHRASE: "keyword"   BROAD: keyword
 */
function formatNegative(text, matchType) {
  if (matchType === 'EXACT') {
    return '[' + text + ']';
  } else if (matchType === 'PHRASE') {
    return '"' + text + '"';
  } else {
    return text; // BROAD
  }
}

/**
 * Add a negative keyword to a campaign (or log in DRY_RUN mode).
 * Checks for duplicates by scanning existing campaign negatives.
 */
function addNegative_(campaign, formattedKw, rawText, matchType, stats) {
  var campaignName = campaign.getName();

  // Check if this negative already exists
  var existingNegatives;
  try {
    existingNegatives = campaign.negativeKeywords().get();
  } catch (e) {
    // Shopping campaigns may use different API
    existingNegatives = null;
  }

  if (existingNegatives) {
    while (existingNegatives.hasNext()) {
      var existing = existingNegatives.next();
      if (existing.getText().toLowerCase() === rawText.toLowerCase() &&
          existing.getMatchType() === matchType) {
        Logger.log('  SKIP (exists): ' + formattedKw + ' → ' + campaignName);
        stats.skipped++;
        return;
      }
    }
  }

  if (DRY_RUN) {
    Logger.log('  [DRY RUN] WOULD ADD: ' + formattedKw + ' → ' + campaignName);
    stats.added++;
  } else {
    try {
      campaign.createNegativeKeyword(formattedKw);
      Logger.log('  ADDED: ' + formattedKw + ' → ' + campaignName);
      stats.added++;
    } catch (e) {
      Logger.log('  FAILED: ' + formattedKw + ' → ' + campaignName + ' | ' + e.message);
      stats.failed++;
    }
  }
}
