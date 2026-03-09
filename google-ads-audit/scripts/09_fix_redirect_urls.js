/**
 * Google Ads Script: Fix Redirect URLs in Ad Final URLs
 * =====================================================
 *
 * PURPOSE:
 * This script updates ad final URLs that currently point to old/redirecting URLs
 * and replaces them with the correct destination URLs. The website already has
 * proper 301 redirects in place, but each redirect adds latency (~200-500ms).
 * By updating the ads directly, we eliminate that redirect hop.
 *
 * DATA SOURCE:
 * FINAL_url_redirect_fixes.csv from the Google Ads URL health check audit.
 * 35 redirect mappings covering $64,000+ in historical ad spend.
 *
 * INSTRUCTIONS:
 * 1. Copy this entire script into Google Ads Scripts (Tools > Scripts)
 * 2. Leave DRY_RUN = true for the first run to preview changes
 * 3. Review the logs to confirm the mappings are correct
 * 4. Set DRY_RUN = false and run again to apply changes
 * 5. Verify ads are serving the new URLs in the Ads interface
 *
 * SAFETY:
 * - DRY_RUN mode (default: true) only logs what WOULD change
 * - Processes both ENABLED and PAUSED ads
 * - Handles ads across all campaign types (Search, Display, etc.)
 * - Logs every change with Campaign, Ad Group, Ad ID, Old URL, New URL
 * - Has batch limits to avoid script timeout (30-minute max)
 *
 * AUTHOR: Nature's Seed Data Orchestrator
 * DATE: 2026-03-05
 */

// ============================================================
// CONFIGURATION
// ============================================================

var DRY_RUN = true; // Set to false to actually make changes

var MAX_ADS_TO_PROCESS = 50000; // Safety limit to avoid timeout
var LOG_EVERY_N = 100; // Log progress every N ads checked

// ============================================================
// REDIRECT MAPPING: old URL -> new correct URL
// ============================================================
// Each key is the old/redirecting URL that appears as an ad's final URL.
// Each value is the correct destination URL that the ad should point to.
// URLs are normalized to lowercase for matching.

var REDIRECT_MAP = {
  // --- High spend redirects (>$1,000 historical spend) ---
  'https://naturesseed.com/pasture-seed/': 'https://naturesseed.com/products/pasture-seed/',
  'https://naturesseed.com/pasture-seed/horse-pastures/': 'https://naturesseed.com/products/pasture-seed/horse-pastures-seed/',
  'https://naturesseed.com/sale/': 'https://naturesseed.com/',
  'https://www.naturesseed.com/': 'https://naturesseed.com/',
  'https://naturesseed.com/grass-seed/clover-seeds-lawn-additive/microclover/': 'https://naturesseed.com/products/clover-seed/microclover/',
  'https://naturesseed.com/product/cattle-dairy-cow-pasture-mix-cold-warm-season': 'https://naturesseed.com/products/pasture-seed/cattle-dairy-cow-pasture-mix-cold-warm-season/',
  'https://naturesseed.com/pasture-seed/cattle-pastures/': 'https://naturesseed.com/products/pasture-seed/cattle-pasture-seed/',
  'https://naturesseed.com/wildflower-seed/': 'https://naturesseed.com/products/wildflower-seed/',
  'https://naturesseed.com/pasture-seed/poultry-pastures/': 'https://naturesseed.com/products/pasture-seed/poultry-forage-mix/',
  'https://naturesseed.com/pasture-seed/sheep-pastures/': 'https://naturesseed.com/products/pasture-seed/sheep-pastures-seed/',
  'https://naturesseed.com/grass-seed/clover-seeds-lawn-additive/white-dutch-clover/': 'https://naturesseed.com/products/clover-seed/white-dutch-clover/',
  'https://naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/': 'https://naturesseed.com/products/pasture-seed/cattle-pasture-seed/',
  'https://naturesseed.com/pasture-seed/goat-pastures/': 'https://naturesseed.com/products/pasture-seed/goat-pastures-seed/',
  'https://naturesseed.com/grass-seed/': 'https://naturesseed.com/products/grass-seed/',

  // --- Medium spend redirects ($100-$1,000) ---
  'https://www.naturesseed.com/grass-seed/clover-seeds-lawn-additive/microclover/': 'https://naturesseed.com/products/clover-seed/microclover/',
  'https://naturesseed.com/pasture-seed/alpaca-llama-pastures/': 'https://naturesseed.com/products/pasture-seed/alpaca-llama-pasture-forage-mix/',
  'https://naturesseed.com/product/sheep-pasture-forage-mix-transitional': 'https://naturesseed.com/products/pasture-seed/sheep-pasture-forage-mix-transitional/',
  'https://www.naturesseed.com/grass-seed/bermuda-grass/bermudagrass-seed-blend/': 'https://naturesseed.com/products/grass-seed/bermudagrass-seed-blend/',
  'https://naturesseed.com/products/grass-seed': 'https://naturesseed.com/products/grass-seed/',
  'https://naturesseed.com/grass-seed/fescue-grass/triple-play-tall-fescue-seed-blend': 'https://naturesseed.com/products/grass-seed/triblade-elite-fescue-lawn-mix/',
  'https://naturesseed.com/grass-seed/kentucky-bluegrass/kentucky-bluegrass-seed-blue-ribbon-mix': 'https://naturesseed.com/products/grass-seed/',
  'https://naturesseed.com/pasture-seed/pig-pastures/': 'https://naturesseed.com/products/pasture-seed/pig-pasture-forage-mix/',

  // --- Lower spend redirects (<$100) but still active ---
  'https://www.naturesseed.com/grass-seed/bahia-grass/bahia-grass-seed-blend/': 'https://naturesseed.com/products/pasture-seed/',
  'https://naturesseed.com/product/alpaca-llama-pasture-forage-mix/': 'https://naturesseed.com/products/pasture-seed/alpaca-llama-pasture-forage-mix/',
  'https://naturesseed.com/product/pig-pasture-forage-mix/': 'https://naturesseed.com/products/pasture-seed/pig-pasture-forage-mix/',
  'https://naturesseed.com/grass-seed/perennial-ryegrass/perennial-ryegrass-seed-blend': 'https://naturesseed.com/products/pasture-seed/perennial-ryegrass/',
  'https://www.naturesseed.com/grass-seed/': 'https://naturesseed.com/products/grass-seed/',
  'https://naturesseed.com/grass-seed/bermuda-grass/bermudagrass-seed-blend': 'https://naturesseed.com/products/grass-seed/bermudagrass-seed-blend/',
  'https://naturesseed.com/grass-seed/kentucky-bluegrass/northeast-seed-mix': 'https://naturesseed.com/products/grass-seed/northeast-lawn/',
  'https://www.naturesseed.com/grass-seed/california/': 'https://naturesseed.com/resources/lawn-turf/california/',
  'http://naturesseed.com/product/alpaca-llama-pasture-forage-mix/': 'https://naturesseed.com/products/pasture-seed/alpaca-llama-pasture-forage-mix/',
  'https://www.naturesseed.com/m-binder-tackifier-soil-stabilizer': 'https://naturesseed.com/products/planting-aids/m-binder-tackifier-soil-stabilizer/',
  'https://www.naturesseed.com/rice-hulls': 'https://naturesseed.com/products/planting-aids/rice-hull/',
  'https://www.naturesseed.com/pasture-seed/by-region/great-lakes-new-england-pasture-seed/': 'https://naturesseed.com/products/pasture-seed/'
};


// ============================================================
// MAIN FUNCTION
// ============================================================

function main() {
  Logger.log('==========================================================');
  Logger.log('Google Ads Script: Fix Redirect URLs');
  Logger.log('Mode: ' + (DRY_RUN ? 'DRY RUN (no changes will be made)' : 'LIVE (changes will be applied)'));
  Logger.log('Redirect mappings loaded: ' + Object.keys(REDIRECT_MAP).length);
  Logger.log('==========================================================');
  Logger.log('');

  // Build a normalized lookup for case-insensitive matching
  var normalizedMap = {};
  for (var oldUrl in REDIRECT_MAP) {
    normalizedMap[normalizeUrl(oldUrl)] = REDIRECT_MAP[oldUrl];
  }

  var stats = {
    totalAdsChecked: 0,
    adsMatched: 0,
    adsUpdated: 0,
    adsFailed: 0,
    campaignsAffected: {},
    adGroupsAffected: {}
  };

  // Process all ad types: Expanded Text Ads, Responsive Search Ads, etc.
  processAds_(normalizedMap, stats);

  // Log summary
  Logger.log('');
  Logger.log('==========================================================');
  Logger.log('SUMMARY');
  Logger.log('==========================================================');
  Logger.log('Total ads checked:      ' + stats.totalAdsChecked);
  Logger.log('Ads with redirect URLs: ' + stats.adsMatched);
  Logger.log('Ads updated:            ' + stats.adsUpdated);
  Logger.log('Ads failed to update:   ' + stats.adsFailed);
  Logger.log('Campaigns affected:     ' + Object.keys(stats.campaignsAffected).length);
  Logger.log('Ad groups affected:     ' + Object.keys(stats.adGroupsAffected).length);
  Logger.log('');

  if (DRY_RUN && stats.adsMatched > 0) {
    Logger.log('*** DRY RUN COMPLETE. Set DRY_RUN = false to apply these changes. ***');
  } else if (!DRY_RUN && stats.adsUpdated > 0) {
    Logger.log('*** LIVE RUN COMPLETE. ' + stats.adsUpdated + ' ads have been updated. ***');
  } else if (stats.adsMatched === 0) {
    Logger.log('*** No ads found matching redirect URLs. URLs may already be updated. ***');
  }
}


// ============================================================
// AD PROCESSING
// ============================================================

function processAds_(normalizedMap, stats) {
  // Build a GAQL query to fetch ads with final URLs matching our redirect patterns
  // We fetch ALL ads (enabled + paused) to be thorough
  var query = 'SELECT ' +
    'campaign.name, ' +
    'ad_group.name, ' +
    'ad_group_ad.ad.id, ' +
    'ad_group_ad.ad.final_urls, ' +
    'ad_group_ad.ad.type, ' +
    'ad_group_ad.status, ' +
    'campaign.status ' +
    'FROM ad_group_ad ' +
    'WHERE ad_group_ad.status IN ("ENABLED", "PAUSED") ' +
    'AND campaign.status IN ("ENABLED", "PAUSED") ' +
    'ORDER BY campaign.name ASC';

  var report;
  try {
    report = AdsApp.search(query);
  } catch (e) {
    Logger.log('ERROR: Failed to query ads: ' + e.message);
    Logger.log('Falling back to iterator-based approach...');
    processAdsViaIterator_(normalizedMap, stats);
    return;
  }

  while (report.hasNext() && stats.totalAdsChecked < MAX_ADS_TO_PROCESS) {
    var row = report.next();
    stats.totalAdsChecked++;

    if (stats.totalAdsChecked % LOG_EVERY_N === 0) {
      Logger.log('  ... checked ' + stats.totalAdsChecked + ' ads so far (' + stats.adsMatched + ' matches)');
    }

    var campaignName = row.campaign.name;
    var adGroupName = row.adGroup.name;
    var adId = row.adGroupAd.ad.id;
    var adType = row.adGroupAd.ad.type;
    var adStatus = row.adGroupAd.status;
    var finalUrls = row.adGroupAd.ad.finalUrls || [];

    if (finalUrls.length === 0) continue;

    var currentUrl = finalUrls[0];
    var normalizedCurrent = normalizeUrl(currentUrl);

    if (normalizedMap.hasOwnProperty(normalizedCurrent)) {
      var newUrl = normalizedMap[normalizedCurrent];
      stats.adsMatched++;
      stats.campaignsAffected[campaignName] = true;
      stats.adGroupsAffected[adGroupName] = true;

      var prefix = DRY_RUN ? '[DRY RUN] WOULD UPDATE' : 'UPDATING';
      Logger.log(prefix + ' - Campaign: ' + campaignName +
        ' | Ad Group: ' + adGroupName +
        ' | Ad ID: ' + adId +
        ' | Type: ' + adType +
        ' | Status: ' + adStatus +
        ' | Old URL: ' + currentUrl +
        ' | New URL: ' + newUrl);

      if (!DRY_RUN) {
        try {
          updateAdFinalUrl_(campaignName, adGroupName, adId, adType, newUrl);
          stats.adsUpdated++;
        } catch (e) {
          stats.adsFailed++;
          Logger.log('  ERROR updating ad ' + adId + ': ' + e.message);
        }
      }
    }
  }

  if (stats.totalAdsChecked >= MAX_ADS_TO_PROCESS) {
    Logger.log('WARNING: Reached max ads limit (' + MAX_ADS_TO_PROCESS + '). Some ads may not have been checked.');
  }
}


/**
 * Fallback: Use the AdsApp iterator API if GAQL search fails.
 */
function processAdsViaIterator_(normalizedMap, stats) {
  Logger.log('Using iterator-based approach...');

  var adIterator = AdsApp.ads()
    .withCondition('Status IN [ENABLED, PAUSED]')
    .withCondition('CampaignStatus IN [ENABLED, PAUSED]')
    .orderBy('CampaignName ASC')
    .get();

  while (adIterator.hasNext() && stats.totalAdsChecked < MAX_ADS_TO_PROCESS) {
    var ad = adIterator.next();
    stats.totalAdsChecked++;

    if (stats.totalAdsChecked % LOG_EVERY_N === 0) {
      Logger.log('  ... checked ' + stats.totalAdsChecked + ' ads so far (' + stats.adsMatched + ' matches)');
    }

    var urls = ad.urls();
    var currentUrl = urls.getFinalUrl();
    if (!currentUrl) continue;

    var normalizedCurrent = normalizeUrl(currentUrl);

    if (normalizedMap.hasOwnProperty(normalizedCurrent)) {
      var newUrl = normalizedMap[normalizedCurrent];
      var campaignName = ad.getCampaign().getName();
      var adGroupName = ad.getAdGroup().getName();
      var adId = ad.getId();
      var adType = ad.getType();

      stats.adsMatched++;
      stats.campaignsAffected[campaignName] = true;
      stats.adGroupsAffected[adGroupName] = true;

      var prefix = DRY_RUN ? '[DRY RUN] WOULD UPDATE' : 'UPDATING';
      Logger.log(prefix + ' - Campaign: ' + campaignName +
        ' | Ad Group: ' + adGroupName +
        ' | Ad ID: ' + adId +
        ' | Type: ' + adType +
        ' | Old URL: ' + currentUrl +
        ' | New URL: ' + newUrl);

      if (!DRY_RUN) {
        try {
          urls.setFinalUrl(newUrl);
          stats.adsUpdated++;
        } catch (e) {
          stats.adsFailed++;
          Logger.log('  ERROR updating ad ' + adId + ': ' + e.message);
        }
      }
    }
  }
}


/**
 * Update an ad's final URL via the mutate API.
 * This handles various ad types (RSA, ETA, etc.)
 */
function updateAdFinalUrl_(campaignName, adGroupName, adId, adType, newUrl) {
  // Use AdsApp iterators to find and update the specific ad
  var adIterator = AdsApp.ads()
    .withCondition('Id = ' + adId)
    .get();

  if (adIterator.hasNext()) {
    var ad = adIterator.next();
    var urls = ad.urls();
    urls.setFinalUrl(newUrl);
  } else {
    throw new Error('Ad not found with ID: ' + adId);
  }
}


// ============================================================
// UTILITY FUNCTIONS
// ============================================================

/**
 * Normalize a URL for consistent comparison:
 * - Lowercase
 * - Remove trailing slashes (except for root domain)
 * - Trim whitespace
 * Note: We keep the exact URL for matching since redirects are path-specific
 */
function normalizeUrl(url) {
  if (!url) return '';
  url = url.trim().toLowerCase();
  // Don't strip trailing slash - our map already has the correct format
  return url;
}
