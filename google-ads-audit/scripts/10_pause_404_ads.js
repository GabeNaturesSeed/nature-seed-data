/**
 * Google Ads Script: Pause Ads with 404 Broken URLs
 * ==================================================
 *
 * PURPOSE:
 * This script finds and pauses ads whose final URLs return HTTP 404 errors.
 * These are ads pointing to pages that no longer exist on naturesseed.com.
 * Most are in the "US | Search | Product Ads" campaign using the pattern
 * www.naturesseed.com/{product-slug} which returns 404.
 *
 * DATA SOURCE:
 * FINAL_url_404_fixes.csv from the Google Ads URL health check audit.
 * 568 unique broken URLs identified across multiple campaigns.
 *
 * INSTRUCTIONS:
 * 1. Copy this entire script into Google Ads Scripts (Tools > Scripts)
 * 2. Leave DRY_RUN = true for the first run to preview which ads will be paused
 * 3. Review the logs carefully - these ads will be PAUSED, not deleted
 * 4. Set DRY_RUN = false and run again to apply changes
 * 5. Paused ads can be re-enabled later if needed
 *
 * SAFETY:
 * - DRY_RUN mode (default: true) only logs what WOULD be paused
 * - Ads are PAUSED, not removed (reversible)
 * - Only processes ads whose final URL EXACTLY matches a known 404 URL
 * - Logs every action with Campaign, Ad Group, Ad ID, Broken URL
 * - Has batch limits to avoid script timeout
 *
 * NOTE ON REPLACEMENT URLS:
 * Many of these 404 URLs have known replacement URLs (included in the
 * audit CSV). However, since Google Ads cannot automatically redirect
 * product listing ads to new URLs without potentially breaking ad
 * relevance and quality score, the safest approach is to:
 * 1. Pause these broken ads
 * 2. Create new ads with correct URLs manually or via bulk upload
 *
 * AUTHOR: Nature\'s Seed Data Orchestrator
 * DATE: 2026-03-05
 */

// ============================================================
// CONFIGURATION
// ============================================================

var DRY_RUN = true; // Set to false to actually pause ads

var MAX_ADS_TO_PROCESS = 100000; // Safety limit to avoid timeout
var LOG_EVERY_N = 500; // Log progress every N ads checked

// ============================================================
// BROKEN 404 URLs - All URLs that return HTTP 404
// ============================================================
// Generated from FINAL_url_404_fixes.csv audit data.
// Total: 568 unique broken URLs.

var BROKEN_URLS = new Set([
  'https://www.naturesseed.com/african-daisy',
  'https://www.naturesseed.com/alkali-barley',
  'https://www.naturesseed.com/alkali-sacaton',
  'https://www.naturesseed.com/alsike-clover',
  'https://www.naturesseed.com/amity-tall-fescue',
  'https://www.naturesseed.com/annual-ryegrass',
  'https://www.naturesseed.com/annual-sunflower',
  'https://www.naturesseed.com/annual-wildflower-mix',
  'https://www.naturesseed.com/arizona-fescue',
  'https://www.naturesseed.com/arizona-lupine',
  'https://www.naturesseed.com/arizona-poppy',
  'https://www.naturesseed.com/arrowleaf-balsamroot',
  'https://www.naturesseed.com/arroyo-lupine',
  'https://www.naturesseed.com/aspen-daisy',
  'https://www.naturesseed.com/baby-blue-eyes',
  'https://www.naturesseed.com/baby-s-breath',
  'https://www.naturesseed.com/baby-snapdragon',
  'https://www.naturesseed.com/bachelor-button',
  'https://www.naturesseed.com/bahia-grass-seed-blend',
  'https://www.naturesseed.com/bay-area-wildflower-mix',
  'https://www.naturesseed.com/bee-pollinator-mix',
  'https://www.naturesseed.com/bermudagrass-seed-blend',
  'https://www.naturesseed.com/big-bluegrass',
  'https://www.naturesseed.com/big-bluestem',
  'https://www.naturesseed.com/big-squirreltail',
  'https://www.naturesseed.com/bird-s-eye-gilia',
  'https://www.naturesseed.com/birdsfoot-trefoil',
  'https://www.naturesseed.com/black-eyed-susan',
  'https://www.naturesseed.com/black-sage',
  'https://www.naturesseed.com/blando-brome-grass',
  'https://www.naturesseed.com/blanket-flower',
  'https://www.naturesseed.com/blue-eyed-grass',
  'https://www.naturesseed.com/blue-grama',
  'https://www.naturesseed.com/blue-mountain-penstemon',
  'https://www.naturesseed.com/blue-wildrye',
  'https://www.naturesseed.com/bluebunch-wheatgrass',
  'https://www.naturesseed.com/bottlebrush-squirreltail',
  'https://www.naturesseed.com/buffalograss-seed-blend',
  'https://www.naturesseed.com/butterfly-milkweed',
  'https://www.naturesseed.com/butterfly-pollinator-mix',
  'https://www.naturesseed.com/california-and-more-wildflower-mix',
  'https://www.naturesseed.com/california-barley',
  'https://www.naturesseed.com/california-bluebell',
  'https://www.naturesseed.com/california-brome-grass',
  'https://www.naturesseed.com/california-buckwheat',
  'https://www.naturesseed.com/california-bush-sunflower',
  'https://www.naturesseed.com/california-coastal-native-wildflower-mix',
  'https://www.naturesseed.com/california-erosion-control-mix',
  'https://www.naturesseed.com/california-goldfields',
  'https://www.naturesseed.com/california-habitat-mix',
  'https://www.naturesseed.com/california-melic',
  'https://www.naturesseed.com/california-native-erosion-control-mix',
  'https://www.naturesseed.com/california-native-pollinator-wildflower-mix',
  'https://www.naturesseed.com/california-native-wildflower-mix',
  'https://www.naturesseed.com/california-phacelia',
  'https://www.naturesseed.com/california-poppy',
  'https://www.naturesseed.com/california-sagebrush',
  'https://www.naturesseed.com/canada-bluegrass',
  'https://www.naturesseed.com/canada-goldenrod',
  'https://www.naturesseed.com/catalogsearch/result/?q=clover',
  'https://www.naturesseed.com/catalogsearch/result/?q=perennial+ryegrass',
  'https://www.naturesseed.com/cattle-spinach',
  'https://www.naturesseed.com/central-valley-wildflower-mix',
  'https://www.naturesseed.com/cereal-rye',
  'https://www.naturesseed.com/chaparral-sage-scrub-mix',
  'https://www.naturesseed.com/chaparral-yucca',
  'https://www.naturesseed.com/chewings-fescue-grass',
  'https://www.naturesseed.com/chinese-houses',
  'https://www.naturesseed.com/cicer-milkvetch',
  'https://www.naturesseed.com/clasping-coneflower',
  'https://www.naturesseed.com/clustered-tarweed',
  'https://www.naturesseed.com/coast-range-melic',
  'https://www.naturesseed.com/coastal-california-poppy',
  'https://www.naturesseed.com/coastal-goldenbush',
  'https://www.naturesseed.com/coastal-gumweed',
  'https://www.naturesseed.com/coastal-sage-scrub-mix',
  'https://www.naturesseed.com/colorado-columbine',
  'https://www.naturesseed.com/common-bermudagrass',
  'https://www.naturesseed.com/common-buckwheat',
  'https://www.naturesseed.com/common-flax',
  'https://www.naturesseed.com/common-milkweed',
  'https://www.naturesseed.com/common-vervain',
  'https://www.naturesseed.com/compact-bioswale-mix',
  'https://www.naturesseed.com/coulter-s-globemallow',
  'https://www.naturesseed.com/creek-clover',
  'https://www.naturesseed.com/creeping-foxtail',
  'https://www.naturesseed.com/creeping-red-fescue-grass',
  'https://www.naturesseed.com/creeping-wildrye',
  'https://www.naturesseed.com/creosote-bush',
  'https://www.naturesseed.com/crested-wheatgrass',
  'https://www.naturesseed.com/crimson-clover',
  'https://www.naturesseed.com/dahurian-wildrye',
  'https://www.naturesseed.com/deer-resistant-wildflower-mix',
  'https://www.naturesseed.com/desert-bluebells',
  'https://www.naturesseed.com/desert-globemallow',
  'https://www.naturesseed.com/desert-lupine',
  'https://www.naturesseed.com/desert-marigold',
  'https://www.naturesseed.com/desert-sage-scrub-mix',
  'https://www.naturesseed.com/desert-sand-verbena',
  'https://www.naturesseed.com/desert-senna',
  'https://www.naturesseed.com/dotseed-plantain',
  'https://www.naturesseed.com/drummond-phlox',
  'https://www.naturesseed.com/eastern-red-columbine',
  'https://www.naturesseed.com/ed-gedling-lupine',
  'https://www.naturesseed.com/fernleaf-biscuitroot',
  'https://www.naturesseed.com/field-pea',
  'https://www.naturesseed.com/fine-fescue-grass-seed-mix',
  'https://www.naturesseed.com/five-spot',
  'https://www.naturesseed.com/florida-tropics-alpaca-llama-forage-mix',
  'https://www.naturesseed.com/florida-tropics-beef-cattle-forage-mix',
  'https://www.naturesseed.com/florida-tropics-big-game-food-plot-mix',
  'https://www.naturesseed.com/florida-tropics-bison-forage-mix',
  'https://www.naturesseed.com/florida-tropics-dairy-cow-forage-mix',
  'https://www.naturesseed.com/florida-tropics-dryland-pasture-mix',
  'https://www.naturesseed.com/florida-tropics-erosion-control-mix',
  'https://www.naturesseed.com/florida-tropics-goat-forage-mix',
  'https://www.naturesseed.com/florida-tropics-honey-bee-pasture-mix',
  'https://www.naturesseed.com/florida-tropics-horse-forage-mix',
  'https://www.naturesseed.com/florida-tropics-pig-forage-mix',
  'https://www.naturesseed.com/florida-tropics-pollinator-mix',
  'https://www.naturesseed.com/florida-tropics-poultry-forage-mix',
  'https://www.naturesseed.com/florida-tropics-sheep-forage-mix',
  'https://www.naturesseed.com/florida-tropics-upland-game-food-plot-mix',
  'https://www.naturesseed.com/flowering-meadow-mix',
  'https://www.naturesseed.com/foothill-needlegrass',
  'https://www.naturesseed.com/forage-chicory',
  'https://www.naturesseed.com/forage-kochia',
  'https://www.naturesseed.com/forage-radish',
  'https://www.naturesseed.com/fort-miller-clarkia',
  'https://www.naturesseed.com/four-wing-saltbush',
  'https://www.naturesseed.com/foxtail-millet',
  'https://www.naturesseed.com/fremonts-goldfields',
  'https://www.naturesseed.com/garden-cosmos',
  'https://www.naturesseed.com/globe-gilia',
  'https://www.naturesseed.com/golden-lupine',
  'https://www.naturesseed.com/grain-sorghum',
  'https://www.naturesseed.com/great-basin-wildflower-mix',
  'https://www.naturesseed.com/great-lakes-new-england-alpaca-llama-forage-mix',
  'https://www.naturesseed.com/great-lakes-new-england-beef-cattle-forage-mix',
  'https://www.naturesseed.com/great-lakes-new-england-big-game-food-plot-mix',
  'https://www.naturesseed.com/great-lakes-new-england-bison-forage-mix',
  'https://www.naturesseed.com/great-lakes-new-england-dairy-cow-forage-mix',
  'https://www.naturesseed.com/great-lakes-new-england-dryland-pasture-mix',
  'https://www.naturesseed.com/great-lakes-new-england-erosion-control-mix',
  'https://www.naturesseed.com/great-lakes-new-england-goat-forage-mix',
  'https://www.naturesseed.com/great-lakes-new-england-honey-bee-pasture-mix',
  'https://www.naturesseed.com/great-lakes-new-england-horse-forage-mix',
  'https://www.naturesseed.com/great-lakes-new-england-pig-forage-mix',
  'https://www.naturesseed.com/great-lakes-new-england-pollinator-mix',
  'https://www.naturesseed.com/great-lakes-new-england-poultry-forage-mix',
  'https://www.naturesseed.com/great-lakes-new-england-sheep-forage-mix',
  'https://www.naturesseed.com/great-lakes-new-england-upland-game-food-plot-mix',
  'https://www.naturesseed.com/great-plains-alpaca-llama-forage-mix',
  'https://www.naturesseed.com/great-plains-beef-cattle-forage-mix',
  'https://www.naturesseed.com/great-plains-big-game-food-plot-mix',
  'https://www.naturesseed.com/great-plains-bison-forage-mix',
  'https://www.naturesseed.com/great-plains-dairy-cow-forage-mix',
  'https://www.naturesseed.com/great-plains-dryland-pasture-mix',
  'https://www.naturesseed.com/great-plains-erosion-control-mix',
  'https://www.naturesseed.com/great-plains-goat-forage-mix',
  'https://www.naturesseed.com/great-plains-honey-bee-pasture-mix',
  'https://www.naturesseed.com/great-plains-horse-forage-mix',
  'https://www.naturesseed.com/great-plains-pig-forage-mix',
  'https://www.naturesseed.com/great-plains-pollinator-mix',
  'https://www.naturesseed.com/great-plains-poultry-forage-mix',
  'https://www.naturesseed.com/great-plains-sheep-forage-mix',
  'https://www.naturesseed.com/great-plains-upland-game-food-plot-mix',
  'https://www.naturesseed.com/great-plains-wildfire-resistant-mix',
  'https://www.naturesseed.com/gum-plant',
  'https://www.naturesseed.com/hairy-vetch',
  'https://www.naturesseed.com/hard-fescue-grass',
  'https://www.naturesseed.com/hooker-s-evening-primrose',
  'https://www.naturesseed.com/hummingbird-pollinator-mix',
  'https://www.naturesseed.com/hybrid-pearl-millet',
  'https://www.naturesseed.com/hykon-rose-clover',
  'https://www.naturesseed.com/icelandic-poppy',
  'https://www.naturesseed.com/idaho-fescue',
  'https://www.naturesseed.com/imbricate-phacelia',
  'https://www.naturesseed.com/indian-ricegrass',
  'https://www.naturesseed.com/insecta-flora-mix',
  'https://www.naturesseed.com/intermediate-wheatgrass',
  'https://www.naturesseed.com/intermountain-west-alpaca-llama-forage-mix',
  'https://www.naturesseed.com/intermountain-west-beef-cattle-forage-mix',
  'https://www.naturesseed.com/intermountain-west-big-game-food-plot-mix',
  'https://www.naturesseed.com/intermountain-west-bison-forage-mix',
  'https://www.naturesseed.com/intermountain-west-dairy-cow-forage-mix',
  'https://www.naturesseed.com/intermountain-west-dryland-pasture-mix',
  'https://www.naturesseed.com/intermountain-west-erosion-control-mix',
  'https://www.naturesseed.com/intermountain-west-goat-forage-mix',
  'https://www.naturesseed.com/intermountain-west-honey-bee-pasture-mix',
  'https://www.naturesseed.com/intermountain-west-horse-forage-mix',
  'https://www.naturesseed.com/intermountain-west-pollinator-mix',
  'https://www.naturesseed.com/intermountain-west-poultry-forage-mix',
  'https://www.naturesseed.com/intermountain-west-sheep-forage-mix',
  'https://www.naturesseed.com/intermountain-west-upland-game-food-plot-mix',
  'https://www.naturesseed.com/intermountain-west-wildfire-resistant-mix',
  'https://www.naturesseed.com/japanese-millet',
  'https://www.naturesseed.com/jimmys-blue-ribbon-premium-grass-seed-mix',
  'https://www.naturesseed.com/kentucky-bluegrass-seed-blue-ribbon-mix',
  'https://www.naturesseed.com/lacy-phacelia',
  'https://www.naturesseed.com/lance-leaved-coreopsis',
  'https://www.naturesseed.com/lemon-mint',
  'https://www.naturesseed.com/little-barley',
  'https://www.naturesseed.com/little-bluestem',
  'https://www.naturesseed.com/little-seed-muhly',
  'https://www.naturesseed.com/low-growing-wildflower-mix',
  'https://www.naturesseed.com/maximilian-sunflower',
  'https://www.naturesseed.com/meadow-barley',
  'https://www.naturesseed.com/meadow-brome',
  'https://www.naturesseed.com/mexican-gold-poppy',
  'https://www.naturesseed.com/mid-west-mid-atlantic-alpaca-llama-forage-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-beef-cattle-forage-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-big-game-food-plot-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-bison-forage-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-dairy-cow-forage-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-dryland-pasture-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-erosion-control-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-goat-forage-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-honey-bee-pasture-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-horse-forage-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-pollinator-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-poultry-forage-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-sheep-forage-mix',
  'https://www.naturesseed.com/mid-west-mid-atlantic-upland-game-food-plot-mix',
  'https://www.naturesseed.com/midwest-wildflower-mix',
  'https://www.naturesseed.com/miniature-lupine',
  'https://www.naturesseed.com/moss-verbena',
  'https://www.naturesseed.com/mostly-perennial-wildflower-mix',
  'https://www.naturesseed.com/mountain-brome',
  'https://www.naturesseed.com/mountain-garland',
  'https://www.naturesseed.com/mountain-lupine',
  'https://www.naturesseed.com/mountain-phlox',
  'https://www.naturesseed.com/munro-globemallow',
  'https://www.naturesseed.com/narrowleaf-milkweed',
  'https://www.naturesseed.com/native-bioswale-mix',
  'https://www.naturesseed.com/native-fine-fescue-mix',
  'https://www.naturesseed.com/nelson-globemallow',
  'https://www.naturesseed.com/new-england-aster',
  'https://www.naturesseed.com/nodding-needlegrass',
  'https://www.naturesseed.com/northeast-seed-mix',
  'https://www.naturesseed.com/northeast-wildflower-mix',
  'https://www.naturesseed.com/northwest-seed-mix',
  'https://www.naturesseed.com/northwest-wildflower-mix',
  'https://www.naturesseed.com/one-sided-bluegrass',
  'https://www.naturesseed.com/organic-seed-starter-fertilizer-4-6-4',
  'https://www.naturesseed.com/ornamental-bioswale-mix',
  'https://www.naturesseed.com/ornamental-low-growing-native-mix',
  'https://www.naturesseed.com/owl-s-clover',
  'https://www.naturesseed.com/pacific-northwest-alpaca-llama-forage-mix',
  'https://www.naturesseed.com/pacific-northwest-beef-cattle-forage-mix',
  'https://www.naturesseed.com/pacific-northwest-big-game-food-plot-mix',
  'https://www.naturesseed.com/pacific-northwest-bison-forage-mix',
  'https://www.naturesseed.com/pacific-northwest-dairy-cow-forage-mix',
  'https://www.naturesseed.com/pacific-northwest-dryland-pasture-mix',
  'https://www.naturesseed.com/pacific-northwest-erosion-control-mix',
  'https://www.naturesseed.com/pacific-northwest-goat-forage-mix',
  'https://www.naturesseed.com/pacific-northwest-honey-bee-pasture-mix',
  'https://www.naturesseed.com/pacific-northwest-horse-forage-mix',
  'https://www.naturesseed.com/pacific-northwest-pollinator-mix',
  'https://www.naturesseed.com/pacific-northwest-poultry-forage-mix',
  'https://www.naturesseed.com/pacific-northwest-sheep-forage-mix',
  'https://www.naturesseed.com/pacific-northwest-upland-game-food-plot-mix',
  'https://www.naturesseed.com/pacific-northwest-wildfire-resistant-mix',
  'https://www.naturesseed.com/pacific-southwest-alpaca-llama-forage-mix',
  'https://www.naturesseed.com/pacific-southwest-beef-cattle-forage-mix',
  'https://www.naturesseed.com/pacific-southwest-big-game-food-plot-mix',
  'https://www.naturesseed.com/pacific-southwest-bison-forage-mix',
  'https://www.naturesseed.com/pacific-southwest-dairy-cow-forage-mix',
  'https://www.naturesseed.com/pacific-southwest-dryland-pasture-mix',
  'https://www.naturesseed.com/pacific-southwest-erosion-control-mix',
  'https://www.naturesseed.com/pacific-southwest-goat-forage-mix',
  'https://www.naturesseed.com/pacific-southwest-honey-bee-pasture-mix',
  'https://www.naturesseed.com/pacific-southwest-horse-forage-mix',
  'https://www.naturesseed.com/pacific-southwest-pollinator-mix',
  'https://www.naturesseed.com/pacific-southwest-poultry-forage-mix',
  'https://www.naturesseed.com/pacific-southwest-sheep-forage-mix',
  'https://www.naturesseed.com/pacific-southwest-upland-game-food-plot-mix',
  'https://www.naturesseed.com/pacific-southwest-wildfire-resistant-mix',
  'https://www.naturesseed.com/palmer-s-penstemon',
  'https://www.naturesseed.com/parry-penstemon',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/florida-tropics-alpaca-llama-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/great-lakes-new-england-alpaca-llama-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/great-plains-alpaca-llama-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/intermountain-west-alpaca-llama-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/intermountain-west-alpaca-llama-forage-mix/',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/mid-west-mid-atlantic-alpaca-llama-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/pacific-northwest-alpaca-llama-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/pacific-southwest-alpaca-llama-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/south-atlantic-transitional-alpaca-llama-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/southern-subtropics-alpaca-llama-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/southwest-desert-alpaca-llama-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/southwest-semi-arid-steppe-alpaca-llama-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/alpaca-llama-pastures/southwest-transitional-alpaca-llama-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/bison-pastures/florida-tropics-bison-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/bison-pastures/great-lakes-new-england-bison-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/bison-pastures/great-plains-bison-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/bison-pastures/intermountain-west-bison-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/bison-pastures/mid-west-mid-atlantic-bison-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/bison-pastures/pacific-northwest-bison-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/bison-pastures/pacific-southwest-bison-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/bison-pastures/south-atlantic-transitional-bison-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/bison-pastures/southern-subtropics-bison-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/bison-pastures/southwest-desert-bison-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/bison-pastures/southwest-semi-arid-steppe-bison-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/bison-pastures/southwest-transitional-bison-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/florida-tropics-beef-cattle-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/great-lakes-new-england-beef-cattle-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/great-plains-beef-cattle-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/intermountain-west-beef-cattle-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/mid-west-mid-atlantic-beef-cattle-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/pacific-northwest-beef-cattle-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/pacific-southwest-beef-cattle-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/south-atlantic-transitional-beef-cattle-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/southern-subtropics-beef-cattle-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/southwest-desert-beef-cattle-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/southwest-semi-arid-steppe-beef-cattle-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/beef-cattle-forage/southwest-transitional-beef-cattle-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/florida-tropics-dairy-cow-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/great-lakes-new-england-dairy-cow-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/great-lakes-new-england-dairy-cow-forage-mix/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/great-plains-dairy-cow-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/intermountain-west-dairy-cow-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/intermountain-west-dairy-cow-forage-mix/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/mid-west-mid-atlantic-dairy-cow-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/pacific-northwest-dairy-cow-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/pacific-southwest-dairy-cow-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/south-atlantic-transitional-dairy-cow-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/southern-subtropics-dairy-cow-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/southwest-desert-dairy-cow-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/southwest-semi-arid-steppe-dairy-cow-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/cattle-pastures/dairy-cow-forage/southwest-transitional-dairy-cow-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/florida-tropics-goat-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/great-lakes-new-england-goat-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/great-lakes-new-england-goat-forage-mix/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/great-plains-goat-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/intermountain-west-goat-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/mid-west-mid-atlantic-goat-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/pacific-northwest-goat-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/pacific-southwest-goat-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/south-atlantic-transitional-goat-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/southern-subtropics-goat-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/southwest-desert-goat-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/southwest-semi-arid-steppe-goat-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/goat-pastures/southwest-transitional-goat-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/florida-tropics-horse-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/great-lakes-new-england-horse-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/great-plains-horse-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/intermountain-west-horse-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/mid-west-mid-atlantic-horse-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/pacific-northwest-horse-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/pacific-southwest-horse-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/south-atlantic-transitional-horse-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/southern-subtropics-horse-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/southern-subtropics-horse-forage-mix/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/southwest-desert-horse-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/southwest-semi-arid-steppe-horse-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/horse-pastures/southwest-transitional-horse-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/florida-tropics-poultry-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/great-lakes-new-england-poultry-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/great-lakes-new-england-poultry-forage-mix/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/great-plains-poultry-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/intermountain-west-poultry-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/intermountain-west-poultry-forage-mix/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/mid-west-mid-atlantic-poultry-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/pacific-northwest-poultry-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/pacific-southwest-poultry-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/south-atlantic-transitional-poultry-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/southern-subtropics-poultry-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/southwest-desert-poultry-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/southwest-semi-arid-steppe-poultry-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/poultry-pastures/southwest-transitional-poultry-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/florida-tropics-sheep-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/great-lakes-new-england-sheep-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/great-plains-sheep-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/intermountain-west-sheep-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/mid-west-mid-atlantic-sheep-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/pacific-northwest-sheep-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/pacific-southwest-sheep-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/south-atlantic-transitional-sheep-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/southern-subtropics-sheep-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/southern-subtropics-sheep-forage-mix/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/southwest-desert-sheep-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/southwest-semi-arid-steppe-sheep-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/sheep-pastures/southwest-transitional-sheep-forage-blend/',
  'https://www.naturesseed.com/pasture-seed/tortoise-forage-blend/',
  'https://www.naturesseed.com/perennial-ryegrass-seed-blend',
  'https://www.naturesseed.com/plains-coreopsis',
  'https://www.naturesseed.com/prickly-poppy',
  'https://www.naturesseed.com/pubescent-wheatgrass',
  'https://www.naturesseed.com/purple-alyssum',
  'https://www.naturesseed.com/purple-clarkia',
  'https://www.naturesseed.com/purple-foxglove',
  'https://www.naturesseed.com/purple-needlegrass',
  'https://www.naturesseed.com/purple-prairie-clover',
  'https://www.naturesseed.com/red-clover',
  'https://www.naturesseed.com/red-maids',
  'https://www.naturesseed.com/red-mexican-hat',
  'https://www.naturesseed.com/red-ribbons',
  'https://www.naturesseed.com/rocket-larkspur',
  'https://www.naturesseed.com/rocky-mountain-iris',
  'https://www.naturesseed.com/rocky-mountain-penstemon',
  'https://www.naturesseed.com/rocky-mountain-wildflower-mix',
  'https://www.naturesseed.com/san-diego-bentgrass',
  'https://www.naturesseed.com/san-diego-sunflower',
  'https://www.naturesseed.com/sand-dropseed',
  'https://www.naturesseed.com/sandberg-bluegrass',
  'https://www.naturesseed.com/scarlet-flax',
  'https://www.naturesseed.com/scarlet-globemallow',
  'https://www.naturesseed.com/seed-aide-cover-grow-water-retaining-seed-starting-mulch',
  'https://www.naturesseed.com/seed-spreader',
  'https://www.naturesseed.com/shasta-daisy',
  'https://www.naturesseed.com/sheep-fescue-grass',
  'https://www.naturesseed.com/shirley-poppy',
  'https://www.naturesseed.com/showy-goldeneye',
  'https://www.naturesseed.com/showy-milkweed',
  'https://www.naturesseed.com/showy-penstemon',
  'https://www.naturesseed.com/siberian-wheatgrass',
  'https://www.naturesseed.com/sideoats-grama',
  'https://www.naturesseed.com/sierra-garden-wildflower-mix',
  'https://www.naturesseed.com/silky-phacelia',
  'https://www.naturesseed.com/silverleaf-lupine',
  'https://www.naturesseed.com/six-weeks-fescue',
  'https://www.naturesseed.com/sky-lupine',
  'https://www.naturesseed.com/slender-wheatgrass',
  'https://www.naturesseed.com/small-burnet',
  'https://www.naturesseed.com/small-fescue',
  'https://www.naturesseed.com/small-flowered-fiddleneck',
  'https://www.naturesseed.com/smooth-aster',
  'https://www.naturesseed.com/smooth-brome',
  'https://www.naturesseed.com/sonoran-desert-wildflower-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-alpaca-llama-forage-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-beef-cattle-forage-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-big-game-food-plot-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-bison-forage-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-dairy-cow-forage-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-dryland-pasture-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-erosion-control-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-goat-forage-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-honey-bee-pasture-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-horse-forage-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-pollinator-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-poultry-forage-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-sheep-forage-mix',
  'https://www.naturesseed.com/south-atlantic-transitional-upland-game-food-plot-mix',
  'https://www.naturesseed.com/southeast-wildflower-mix',
  'https://www.naturesseed.com/southern-sports-turf-mix',
  'https://www.naturesseed.com/southern-subtropics-alpaca-llama-forage-mix',
  'https://www.naturesseed.com/southern-subtropics-beef-cattle-forage-mix',
  'https://www.naturesseed.com/southern-subtropics-big-game-food-plot-mix',
  'https://www.naturesseed.com/southern-subtropics-bison-forage-mix',
  'https://www.naturesseed.com/southern-subtropics-dairy-cow-forage-mix',
  'https://www.naturesseed.com/southern-subtropics-dryland-pasture-mix',
  'https://www.naturesseed.com/southern-subtropics-erosion-control-mix',
  'https://www.naturesseed.com/southern-subtropics-goat-forage-mix',
  'https://www.naturesseed.com/southern-subtropics-honey-bee-pasture-mix',
  'https://www.naturesseed.com/southern-subtropics-horse-forage-mix',
  'https://www.naturesseed.com/southern-subtropics-pollinator-mix',
  'https://www.naturesseed.com/southern-subtropics-poultry-forage-mix',
  'https://www.naturesseed.com/southern-subtropics-sheep-forage-mix',
  'https://www.naturesseed.com/southern-subtropics-upland-game-food-plot-mix',
  'https://www.naturesseed.com/southwest-desert-alpaca-llama-forage-mix',
  'https://www.naturesseed.com/southwest-desert-beef-cattle-forage-mix',
  'https://www.naturesseed.com/southwest-desert-big-game-food-plot-mix',
  'https://www.naturesseed.com/southwest-desert-bison-forage-mix',
  'https://www.naturesseed.com/southwest-desert-dairy-cow-forage-mix',
  'https://www.naturesseed.com/southwest-desert-dryland-pasture-mix',
  'https://www.naturesseed.com/southwest-desert-erosion-control-mix',
  'https://www.naturesseed.com/southwest-desert-goat-forage-mix',
  'https://www.naturesseed.com/southwest-desert-honey-bee-pasture-mix',
  'https://www.naturesseed.com/southwest-desert-horse-forage-mix',
  'https://www.naturesseed.com/southwest-desert-pollinator-mix',
  'https://www.naturesseed.com/southwest-desert-poultry-forage-mix',
  'https://www.naturesseed.com/southwest-desert-sheep-forage-mix',
  'https://www.naturesseed.com/southwest-desert-upland-game-food-plot-mix',
  'https://www.naturesseed.com/southwest-desert-wildfire-resistant-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-alpaca-llama-forage-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-beef-cattle-forage-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-big-game-food-plot-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-bison-forage-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-dairy-cow-forage-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-dryland-pasture-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-erosion-control-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-goat-forage-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-honey-bee-pasture-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-horse-forage-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-pollinator-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-poultry-forage-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-sheep-forage-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-upland-game-food-plot-mix',
  'https://www.naturesseed.com/southwest-semi-arid-steppe-wildfire-resistant-mix',
  'https://www.naturesseed.com/southwest-transitional-alpaca-llama-forage-mix',
  'https://www.naturesseed.com/southwest-transitional-beef-cattle-forage-mix',
  'https://www.naturesseed.com/southwest-transitional-big-game-food-plot-mix',
  'https://www.naturesseed.com/southwest-transitional-bison-forage-mix',
  'https://www.naturesseed.com/southwest-transitional-dairy-cow-forage-mix',
  'https://www.naturesseed.com/southwest-transitional-dryland-pasture-mix',
  'https://www.naturesseed.com/southwest-transitional-erosion-control-mix',
  'https://www.naturesseed.com/southwest-transitional-goat-forage-mix',
  'https://www.naturesseed.com/southwest-transitional-honey-bee-pasture-mix',
  'https://www.naturesseed.com/southwest-transitional-horse-forage-mix',
  'https://www.naturesseed.com/southwest-transitional-pollinator-mix',
  'https://www.naturesseed.com/southwest-transitional-poultry-forage-mix',
  'https://www.naturesseed.com/southwest-transitional-sheep-forage-mix',
  'https://www.naturesseed.com/southwest-transitional-upland-game-food-plot-mix',
  'https://www.naturesseed.com/southwest-transitional-wildfire-resistant-mix',
  'https://www.naturesseed.com/southwest-wildflower-mix',
  'https://www.naturesseed.com/spanish-clover',
  'https://www.naturesseed.com/specialty-seed/honey-bee-blends/great-lakes-new-england-honey-bee-pasture-blend/',
  'https://www.naturesseed.com/specialty-seed/honey-bee-blends/intermountain-west-honey-bee-pasture-blend/',
  'https://www.naturesseed.com/specialty-seed/honey-bee-blends/pacific-southwest-honey-bee-pasture-blend/',
  'https://www.naturesseed.com/specialty-seed/honey-bee-blends/southern-subtropics-honey-bee-pasture-blend/',
  'https://www.naturesseed.com/spike-bentgrass',
  'https://www.naturesseed.com/spiked-gayfeather',
  'https://www.naturesseed.com/splitleaf-indian-paintbrush',
  'https://www.naturesseed.com/spring-fever-wildflower-mix',
  'https://www.naturesseed.com/standing-cypress',
  'https://www.naturesseed.com/strawberry-clover',
  'https://www.naturesseed.com/streambank-wheatgrass',
  'https://www.naturesseed.com/sulphur-cosmos',
  'https://www.naturesseed.com/sun-shade-seed-mix',
  'https://www.naturesseed.com/sun-shade-wildflower-mix',
  'https://www.naturesseed.com/sweet-alyssum',
  'https://www.naturesseed.com/sweet-pea',
  'https://www.naturesseed.com/sweet-william-catchfly',
  'https://www.naturesseed.com/tall-fescue',
  'https://www.naturesseed.com/tall-fescue-utility-blend',
  'https://www.naturesseed.com/tall-wheatgrass',
  'https://www.naturesseed.com/tansy-aster',
  'https://www.naturesseed.com/thickspike-wheatgrass',
  'https://www.naturesseed.com/tidy-tips',
  'https://www.naturesseed.com/tomcat-clover',
  'https://www.naturesseed.com/tortoise-forage-mix',
  'https://www.naturesseed.com/tracys-clarkia',
  'https://www.naturesseed.com/tree-clover',
  'https://www.naturesseed.com/tufted-hairgrass',
  'https://www.naturesseed.com/twca-water-wise-heavy-traffic-mix',
  'https://www.naturesseed.com/twca-water-wise-northern-sports-mix',
  'https://www.naturesseed.com/twca-water-wise-northwest-mix',
  'https://www.naturesseed.com/twca-water-wise-shade-mix',
  'https://www.naturesseed.com/twca-water-wise-tall-fescue-blend',
  'https://www.naturesseed.com/utah-sweetvetch',
  'https://www.naturesseed.com/venus-penstemon',
  'https://www.naturesseed.com/water-wise-bluegrass-blend',
  'https://www.naturesseed.com/western-low-water-use-pollinator-mix',
  'https://www.naturesseed.com/western-wheatgrass',
  'https://www.naturesseed.com/western-yarrow',
  'https://www.naturesseed.com/white-clover',
  'https://www.naturesseed.com/white-dutch-clover',
  'https://www.naturesseed.com/white-evening-primrose',
  'https://www.naturesseed.com/white-mustard',
  'https://www.naturesseed.com/white-proso-millet',
  'https://www.naturesseed.com/white-sweet-clover',
  'https://www.naturesseed.com/wild-bergamot',
  'https://www.naturesseed.com/wild-lupine',
  'https://www.naturesseed.com/wildflower-seed/regional-wildflower-mixes/california-wildflower-blend/',
  'https://www.naturesseed.com/wildflower-seed/regional-wildflower-mixes/midwest-wildflower-blend/',
  'https://www.naturesseed.com/wildflower-seed/regional-wildflower-mixes/northeast-wildflower-blend/',
  'https://www.naturesseed.com/wildflower-seed/regional-wildflower-mixes/northwest-wildflower-blend/',
  'https://www.naturesseed.com/wildflower-seed/regional-wildflower-mixes/rocky-mountain-wildflower-blend/',
  'https://www.naturesseed.com/woolly-sunflower',
  'https://www.naturesseed.com/xerces-central-coast-pollinator-mix',
  'https://www.naturesseed.com/xerces-central-valley-pollinator-mix',
  'https://www.naturesseed.com/yellow-beeplant',
  'https://www.naturesseed.com/yellow-evening-primrose',
  'https://www.naturesseed.com/yellow-prairie-coneflower',
  'https://www.naturesseed.com/yellow-sweet-clover',
  'https://www.naturesseed.com/yellowray-goldfields',
  'https://www.naturesseed.com/zorro-fescue'
]);


// ============================================================
// MAIN FUNCTION
// ============================================================

function main() {
  Logger.log('==========================================================');
  Logger.log('Google Ads Script: Pause 404 Broken URL Ads');
  Logger.log('Mode: ' + (DRY_RUN ? 'DRY RUN (no changes will be made)' : 'LIVE (ads will be paused)'));
  Logger.log('Broken URLs loaded: ' + BROKEN_URLS.size);
  Logger.log('==========================================================');
  Logger.log('');

  var stats = {
    totalAdsChecked: 0,
    adsMatched: 0,
    adsPaused: 0,
    adsAlreadyPaused: 0,
    adsFailed: 0,
    campaignsAffected: {},
    adGroupsAffected: {}
  };

  processAds_(stats);

  // Log summary
  Logger.log('');
  Logger.log('==========================================================');
  Logger.log('SUMMARY');
  Logger.log('==========================================================');
  Logger.log('Total ads checked:         ' + stats.totalAdsChecked);
  Logger.log('Ads with broken 404 URLs:  ' + stats.adsMatched);
  Logger.log('Ads paused (this run):     ' + stats.adsPaused);
  Logger.log('Ads already paused:        ' + stats.adsAlreadyPaused);
  Logger.log('Ads failed to pause:       ' + stats.adsFailed);
  Logger.log('Campaigns affected:        ' + Object.keys(stats.campaignsAffected).length);
  Logger.log('Ad groups affected:        ' + Object.keys(stats.adGroupsAffected).length);
  Logger.log('');

  if (DRY_RUN && stats.adsMatched > 0) {
    Logger.log('*** DRY RUN COMPLETE. Set DRY_RUN = false to pause these ads. ***');
  } else if (!DRY_RUN && stats.adsPaused > 0) {
    Logger.log('*** LIVE RUN COMPLETE. ' + stats.adsPaused + ' ads have been paused. ***');
  } else if (stats.adsMatched === 0) {
    Logger.log('*** No ads found matching broken 404 URLs. They may already be paused or removed. ***');
  }

  // Log affected campaigns for reference
  Logger.log('');
  Logger.log('Campaigns with broken ads:');
  for (var campaign in stats.campaignsAffected) {
    Logger.log('  - ' + campaign + ' (' + stats.campaignsAffected[campaign] + ' ads)');
  }
}


// ============================================================
// AD PROCESSING
// ============================================================

function processAds_(stats) {
  // Use GAQL query to fetch all ads
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
    Logger.log('ERROR: GAQL search failed: ' + e.message);
    Logger.log('Falling back to iterator-based approach...');
    processAdsViaIterator_(stats);
    return;
  }

  while (report.hasNext() && stats.totalAdsChecked < MAX_ADS_TO_PROCESS) {
    var row = report.next();
    stats.totalAdsChecked++;

    if (stats.totalAdsChecked % LOG_EVERY_N === 0) {
      Logger.log('  ... checked ' + stats.totalAdsChecked + ' ads (' + stats.adsMatched + ' matches)');
    }

    var campaignName = row.campaign.name;
    var adGroupName = row.adGroup.name;
    var adId = row.adGroupAd.ad.id;
    var adType = row.adGroupAd.ad.type;
    var adStatus = row.adGroupAd.status;
    var finalUrls = row.adGroupAd.ad.finalUrls || [];

    if (finalUrls.length === 0) continue;

    var currentUrl = finalUrls[0];

    // Check if this URL is in our broken set (exact match)
    if (BROKEN_URLS.has(currentUrl) || BROKEN_URLS.has(currentUrl.replace(/\/$/, '')) || BROKEN_URLS.has(currentUrl + '/')) {
      stats.adsMatched++;

      if (!stats.campaignsAffected[campaignName]) {
        stats.campaignsAffected[campaignName] = 0;
      }
      stats.campaignsAffected[campaignName]++;
      stats.adGroupsAffected[adGroupName] = true;

      if (adStatus === 'PAUSED') {
        stats.adsAlreadyPaused++;
        Logger.log('[ALREADY PAUSED] Campaign: ' + campaignName +
          ' | Ad Group: ' + adGroupName +
          ' | Ad ID: ' + adId +
          ' | Broken URL: ' + currentUrl);
        continue;
      }

      var prefix = DRY_RUN ? '[DRY RUN] WOULD PAUSE' : 'PAUSING';
      Logger.log(prefix + ' - Campaign: ' + campaignName +
        ' | Ad Group: ' + adGroupName +
        ' | Ad ID: ' + adId +
        ' | Type: ' + adType +
        ' | Broken URL: ' + currentUrl);

      if (!DRY_RUN) {
        try {
          pauseAd_(adId);
          stats.adsPaused++;
        } catch (e) {
          stats.adsFailed++;
          Logger.log('  ERROR pausing ad ' + adId + ': ' + e.message);
        }
      }
    }
  }

  if (stats.totalAdsChecked >= MAX_ADS_TO_PROCESS) {
    Logger.log('WARNING: Reached max ads limit. Some ads may not have been checked.');
  }
}


/**
 * Fallback: Use AdsApp iterator API if GAQL fails.
 */
function processAdsViaIterator_(stats) {
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
      Logger.log('  ... checked ' + stats.totalAdsChecked + ' ads (' + stats.adsMatched + ' matches)');
    }

    var currentUrl = ad.urls().getFinalUrl();
    if (!currentUrl) continue;

    if (BROKEN_URLS.has(currentUrl) || BROKEN_URLS.has(currentUrl.replace(/\/$/, '')) || BROKEN_URLS.has(currentUrl + '/')) {
      var campaignName = ad.getCampaign().getName();
      var adGroupName = ad.getAdGroup().getName();
      var adId = ad.getId();
      var adType = ad.getType();
      var isEnabled = ad.isEnabled();

      stats.adsMatched++;

      if (!stats.campaignsAffected[campaignName]) {
        stats.campaignsAffected[campaignName] = 0;
      }
      stats.campaignsAffected[campaignName]++;
      stats.adGroupsAffected[adGroupName] = true;

      if (!isEnabled) {
        stats.adsAlreadyPaused++;
        Logger.log('[ALREADY PAUSED] Campaign: ' + campaignName +
          ' | Ad Group: ' + adGroupName +
          ' | Ad ID: ' + adId +
          ' | Broken URL: ' + currentUrl);
        continue;
      }

      var prefix = DRY_RUN ? '[DRY RUN] WOULD PAUSE' : 'PAUSING';
      Logger.log(prefix + ' - Campaign: ' + campaignName +
        ' | Ad Group: ' + adGroupName +
        ' | Ad ID: ' + adId +
        ' | Type: ' + adType +
        ' | Broken URL: ' + currentUrl);

      if (!DRY_RUN) {
        try {
          ad.pause();
          stats.adsPaused++;
        } catch (e) {
          stats.adsFailed++;
          Logger.log('  ERROR pausing ad ' + adId + ': ' + e.message);
        }
      }
    }
  }
}


/**
 * Pause an ad by ID using the iterator API.
 */
function pauseAd_(adId) {
  var adIterator = AdsApp.ads()
    .withCondition('Id = ' + adId)
    .get();

  if (adIterator.hasNext()) {
    var ad = adIterator.next();
    ad.pause();
  } else {
    throw new Error('Ad not found with ID: ' + adId);
  }
}
