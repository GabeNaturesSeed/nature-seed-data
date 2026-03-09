/**
 * Google Ads Script: Fix URLs on LIVE/ENABLED Ads Only
 * ====================================================
 *
 * PURPOSE:
 * Updates final URLs on the 16 currently ENABLED ads (in ENABLED campaigns)
 * that point to old/redirecting paths. These are ads actively serving traffic.
 *
 * SCOPE:
 * - ONLY processes ads in campaigns with status = ENABLED
 * - ONLY processes ads with status = ENABLED
 * - 16 ads across 3 campaigns: Brand, Animal Seed (Broad), Pasture Exact
 *
 * ISSUES FIXED:
 * 1. Three Brand ETAs using www.naturesseed.com instead of naturesseed.com
 * 2. Old /product/{slug} paths → correct /products/pasture-seed/{slug}
 * 3. Old /pasture-seed/{subcategory}/ paths → /products/pasture-seed/{slug}
 *
 * TOTAL AFFECTED SPEND: ~$12,900 all-time across these 16 ads
 *
 * INSTRUCTIONS:
 * 1. Copy into Google Ads Scripts (Tools > Scripts)
 * 2. Run with DRY_RUN = true (default) to preview changes
 * 3. Review logs to confirm mappings are correct
 * 4. Set DRY_RUN = false and run again to apply
 *
 * SAFETY:
 * - DRY_RUN = true by default (no changes made)
 * - Only touches ENABLED campaigns + ENABLED ads
 * - Logs every match with full context
 *
 * AUTHOR: Nature's Seed Data Orchestrator
 * DATE: 2026-03-05
 * SOURCE: LIVE_STATE_AUDIT.md — Section 7 (Live URL Issues)
 */

// ============================================================
// CONFIGURATION
// ============================================================

var DRY_RUN = true; // Set to false to apply changes

// ============================================================
// URL MAPPINGS — Only for the 16 live ads with issues
// ============================================================
// Source: LIVE_url_issues.csv (all ENABLED ads in ENABLED campaigns)

var REDIRECT_MAP = {

  // --- www. subdomain → canonical domain (3 Brand ETAs) ---
  'https://www.naturesseed.com/':
    'https://naturesseed.com/',

  // --- Old /product/{slug} paths → /products/pasture-seed/{slug} ---
  'https://naturesseed.com/product/cattle-dairy-cow-pasture-mix-cold-warm-season':
    'https://naturesseed.com/products/pasture-seed/cattle-dairy-cow-pasture-mix-cold-warm-season/',

  'https://naturesseed.com/product/sheep-pasture-forage-mix-transitional':
    'https://naturesseed.com/products/pasture-seed/sheep-pasture-forage-mix-transitional/',

  'https://naturesseed.com/product/alpaca-llama-pasture-forage-mix/':
    'https://naturesseed.com/products/pasture-seed/alpaca-llama-pasture-forage-mix/',

  'https://naturesseed.com/product/pig-pasture-forage-mix/':
    'https://naturesseed.com/products/pasture-seed/pig-pasture-forage-mix/',

  'https://naturesseed.com/product/big-game-food-plot-forage-mix/':
    'https://naturesseed.com/products/pasture-seed/big-game-food-plot-forage-mix/',

  // --- Old /pasture-seed/{subcategory}/ → /products/pasture-seed/{slug} ---
  'https://naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/':
    'https://naturesseed.com/products/pasture-seed/cattle-pasture-seed/',

  'https://naturesseed.com/pasture-seed/horse-pastures/':
    'https://naturesseed.com/products/pasture-seed/horse-pastures-seed/',

  'https://naturesseed.com/pasture-seed/sheep-pastures/':
    'https://naturesseed.com/products/pasture-seed/sheep-pastures-seed/',

  'https://naturesseed.com/pasture-seed/alpaca-llama-pastures/':
    'https://naturesseed.com/products/pasture-seed/alpaca-llama-pasture-forage-mix/',

  'https://naturesseed.com/pasture-seed/goat-pastures/':
    'https://naturesseed.com/products/pasture-seed/goat-pastures-seed/'
};

// ============================================================
// EXPECTED AD MATCHES (for verification)
// ============================================================
// These are the exact ad IDs from LIVE_url_issues.csv.
// The script will flag if it finds unexpected matches.

var EXPECTED_AD_IDS = [
  '272079888904', '272079888901', '272079888907',   // Brand ETAs (www.)
  '771352317042',                                     // Cattle /product/ path
  '771352317054',                                     // Sheep /product/ path
  '771352317048',                                     // Llama /product/ path
  '773132599426',                                     // Pig /product/ path
  '773132599570',                                     // Bison /product/ path
  '773132599438',                                     // Cattle old /pasture-seed/ path
  '773132599351',                                     // Horse old /pasture-seed/ path
  '773132599198',                                     // Sheep old /pasture-seed/ path
  '773132599345',                                     // Alpaca old /pasture-seed/ path
  '773132599366',                                     // Llama old /pasture-seed/ path (0 spend)
  '773132599387',                                     // Goat old /pasture-seed/ path (0 spend)
  '773132599390'                                      // Goat old /pasture-seed/ path (0 spend)
];

// ============================================================
// MAIN FUNCTION
// ============================================================

function main() {
  Logger.log('==========================================================');
  Logger.log('Google Ads Script: Fix LIVE Ad URLs');
  Logger.log('Mode: ' + (DRY_RUN ? 'DRY RUN (preview only)' : 'LIVE (applying changes)'));
  Logger.log('URL mappings: ' + Object.keys(REDIRECT_MAP).length);
  Logger.log('Expected matching ads: ' + EXPECTED_AD_IDS.length);
  Logger.log('==========================================================');
  Logger.log('');

  // Build normalized lookup
  var normalizedMap = {};
  for (var oldUrl in REDIRECT_MAP) {
    normalizedMap[normalizeUrl(oldUrl)] = REDIRECT_MAP[oldUrl];
  }

  var stats = {
    totalChecked: 0,
    matched: 0,
    updated: 0,
    failed: 0,
    unexpected: 0,
    details: []
  };

  // GAQL query: ONLY enabled ads in enabled campaigns
  var query = 'SELECT ' +
    'campaign.name, ' +
    'ad_group.name, ' +
    'ad_group_ad.ad.id, ' +
    'ad_group_ad.ad.final_urls, ' +
    'ad_group_ad.ad.type, ' +
    'ad_group_ad.status, ' +
    'campaign.status ' +
    'FROM ad_group_ad ' +
    'WHERE ad_group_ad.status = "ENABLED" ' +
    'AND campaign.status = "ENABLED" ' +
    'ORDER BY campaign.name ASC';

  var report;
  try {
    report = AdsApp.search(query);
  } catch (e) {
    Logger.log('ERROR: GAQL query failed: ' + e.message);
    Logger.log('Falling back to iterator...');
    processViaIterator_(normalizedMap, stats);
    logSummary_(stats);
    return;
  }

  while (report.hasNext()) {
    var row = report.next();
    stats.totalChecked++;

    var campaignName = row.campaign.name;
    var adGroupName = row.adGroup.name;
    var adId = String(row.adGroupAd.ad.id);
    var adType = row.adGroupAd.ad.type;
    var finalUrls = row.adGroupAd.ad.finalUrls || [];

    if (finalUrls.length === 0) continue;

    var currentUrl = finalUrls[0];
    var normalizedCurrent = normalizeUrl(currentUrl);

    if (normalizedMap.hasOwnProperty(normalizedCurrent)) {
      var newUrl = normalizedMap[normalizedCurrent];
      stats.matched++;

      // Check if this is an expected match
      var isExpected = EXPECTED_AD_IDS.indexOf(adId) !== -1;
      if (!isExpected) {
        stats.unexpected++;
        Logger.log('⚠ UNEXPECTED MATCH (not in expected list):');
      }

      var prefix = DRY_RUN ? '[DRY RUN] WOULD UPDATE' : 'UPDATING';
      Logger.log(prefix +
        '\n  Campaign: ' + campaignName +
        '\n  Ad Group: ' + adGroupName +
        '\n  Ad ID:    ' + adId +
        '\n  Type:     ' + adType +
        '\n  Old URL:  ' + currentUrl +
        '\n  New URL:  ' + newUrl +
        '\n  Expected: ' + (isExpected ? 'YES' : 'NO — REVIEW THIS') +
        '\n');

      stats.details.push({
        campaign: campaignName,
        adGroup: adGroupName,
        adId: adId,
        oldUrl: currentUrl,
        newUrl: newUrl
      });

      if (!DRY_RUN) {
        try {
          updateAdUrl_(adId, newUrl);
          stats.updated++;
        } catch (e) {
          stats.failed++;
          Logger.log('  ERROR: ' + e.message);
        }
      }
    }
  }

  logSummary_(stats);
}


// ============================================================
// FALLBACK: Iterator-based approach
// ============================================================

function processViaIterator_(normalizedMap, stats) {
  var adIterator = AdsApp.ads()
    .withCondition('Status = ENABLED')
    .withCondition('CampaignStatus = ENABLED')
    .get();

  while (adIterator.hasNext()) {
    var ad = adIterator.next();
    stats.totalChecked++;

    var currentUrl = ad.urls().getFinalUrl();
    if (!currentUrl) continue;

    var normalizedCurrent = normalizeUrl(currentUrl);

    if (normalizedMap.hasOwnProperty(normalizedCurrent)) {
      var newUrl = normalizedMap[normalizedCurrent];
      var adId = String(ad.getId());
      stats.matched++;

      var isExpected = EXPECTED_AD_IDS.indexOf(adId) !== -1;
      if (!isExpected) stats.unexpected++;

      var prefix = DRY_RUN ? '[DRY RUN] WOULD UPDATE' : 'UPDATING';
      Logger.log(prefix +
        '\n  Campaign: ' + ad.getCampaign().getName() +
        '\n  Ad Group: ' + ad.getAdGroup().getName() +
        '\n  Ad ID:    ' + adId +
        '\n  Old URL:  ' + currentUrl +
        '\n  New URL:  ' + newUrl + '\n');

      if (!DRY_RUN) {
        try {
          ad.urls().setFinalUrl(newUrl);
          stats.updated++;
        } catch (e) {
          stats.failed++;
          Logger.log('  ERROR: ' + e.message);
        }
      }
    }
  }
}


// ============================================================
// UPDATE AD URL
// ============================================================

function updateAdUrl_(adId, newUrl) {
  var adIterator = AdsApp.ads()
    .withCondition('Id = ' + adId)
    .get();

  if (adIterator.hasNext()) {
    var ad = adIterator.next();
    ad.urls().setFinalUrl(newUrl);
  } else {
    throw new Error('Ad not found: ' + adId);
  }
}


// ============================================================
// SUMMARY
// ============================================================

function logSummary_(stats) {
  Logger.log('==========================================================');
  Logger.log('SUMMARY');
  Logger.log('==========================================================');
  Logger.log('Enabled ads checked:  ' + stats.totalChecked);
  Logger.log('Matched redirect:     ' + stats.matched + ' (expected: ' + EXPECTED_AD_IDS.length + ')');
  Logger.log('Updated:              ' + stats.updated);
  Logger.log('Failed:               ' + stats.failed);
  Logger.log('Unexpected matches:   ' + stats.unexpected);
  Logger.log('');

  if (stats.matched < EXPECTED_AD_IDS.length) {
    Logger.log('⚠ FEWER MATCHES THAN EXPECTED. Some expected ads may already be updated or paused.');
  }

  if (stats.unexpected > 0) {
    Logger.log('⚠ UNEXPECTED MATCHES FOUND. Review the logs above — additional ads matched the redirect patterns.');
  }

  if (DRY_RUN && stats.matched > 0) {
    Logger.log('');
    Logger.log('*** DRY RUN COMPLETE. Set DRY_RUN = false to apply. ***');
  } else if (!DRY_RUN && stats.updated > 0) {
    Logger.log('');
    Logger.log('*** DONE. ' + stats.updated + ' ad URLs updated. ***');
  }
}


// ============================================================
// UTILITY
// ============================================================

function normalizeUrl(url) {
  if (!url) return '';
  return url.trim().toLowerCase();
}
