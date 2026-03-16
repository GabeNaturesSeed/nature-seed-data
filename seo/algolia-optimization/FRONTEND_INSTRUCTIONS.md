# Frontend Search Improvements — Implementation Guide

**For:** Frontend designer/developer
**Date:** March 4, 2026
**Scope:** Two features for the Algolia search dropdown on naturesseed.com

---

## Feature 1: Contextual Tag Pills on Search Results

### What it does
When a customer searches contextually (e.g., "drought tolerant lawn"), each product result shows small pill/badge tags that confirm *why* that product matched their search. This reinforces that the search understood their intent.

### Data available
Every product record in Algolia now has a `contextual_tags` array field. Example:

```json
{
  "post_title": "Bermuda Grass Seed Mix for Lawns",
  "contextual_tags": [
    "Drought Tolerant",
    "Full Sun",
    "Sports Turf",
    "Perennial",
    "Lawn Seed"
  ]
}
```

### How to implement

**Step 1 — Request `contextual_tags` in the Algolia query**

In `GSNature/dist/js/main.DGpiDnSE.js`, find the multi-index query where products are fetched. Add `contextual_tags` to the `attributesToRetrieve` array:

```js
attributesToRetrieve: [
  "post_title", "permalink", "images", "taxonomies",
  // ... existing fields
  "contextual_tags"  // ADD THIS
]
```

**Step 2 — Match tags to the search query**

When rendering each product result, filter `contextual_tags` to only show tags relevant to the current query. A simple approach: check if any word in the search query appears in the tag text.

```js
function getMatchingTags(query, contextualTags) {
  if (!contextualTags || !contextualTags.length) return [];

  const queryWords = query.toLowerCase().split(/\s+/);

  // Map of query keywords → which tags they should surface
  const TAG_TRIGGERS = {
    'drought':     ['Drought Tolerant', 'Water-Wise', 'Low Maintenance'],
    'tolerant':    ['Drought Tolerant', 'Shade Tolerant'],
    'water':       ['Drought Tolerant', 'Water-Wise', 'Low to Moderate Water', 'Moderate Water', 'Regular Water'],
    'shade':       ['Shade Tolerant'],
    'sun':         ['Full Sun'],
    'pollinator':  ['Attracts Pollinators'],
    'bee':         ['Attracts Pollinators'],
    'butterfly':   ['Attracts Pollinators'],
    'native':      ['Native Species', 'California Native'],
    'california':  ['California Native'],
    'erosion':     ['Erosion Control', 'Slopes & Hillsides'],
    'slope':       ['Slopes & Hillsides', 'Erosion Control'],
    'pet':         ['Pet Friendly'],
    'dog':         ['Pet Friendly'],
    'lawn':        ['Lawn Seed', 'Lawn Alternative'],
    'clover':      ['Clover'],
    'cover':       ['Cover Crop'],
    'food':        ['Food Plot'],
    'forage':      ['Forage & Grazing'],
    'grazing':     ['Forage & Grazing'],
    'hay':         ['Hay Production'],
    'wildlife':    ['Wildlife Habitat'],
    'deer':        ['Food Plot', 'Wildlife Habitat'],
    'nitrogen':    ['Nitrogen Fixing'],
    'meadow':      ['Meadow'],
    'perennial':   ['Perennial'],
    'annual':      ['Annual'],
    'cattle':      ['Cattle Forage'],
    'cow':         ['Cattle Forage'],
    'horse':       ['Horse Forage'],
    'sheep':       ['Sheep Forage'],
    'goat':        ['Goat Forage'],
    'chicken':     ['Poultry Forage'],
    'poultry':     ['Poultry Forage'],
    'alpaca':      ['Alpaca & Llama Forage'],
    'llama':       ['Alpaca & Llama Forage'],
    'tortoise':    ['Tortoise Forage'],
    'turtle':      ['Tortoise Forage'],
    'ornamental':  ['Ornamental'],
    'sport':       ['Sports Turf'],
    'turf':        ['Sports Turf', 'Lawn Seed'],
    'low maintenance': ['Low Maintenance'],
  };

  const relevantTags = new Set();
  for (const word of queryWords) {
    const triggers = TAG_TRIGGERS[word];
    if (triggers) {
      triggers.forEach(t => relevantTags.add(t));
    }
  }

  // Also check multi-word triggers
  const queryLower = query.toLowerCase();
  for (const [trigger, tags] of Object.entries(TAG_TRIGGERS)) {
    if (trigger.includes(' ') && queryLower.includes(trigger)) {
      tags.forEach(t => relevantTags.add(t));
    }
  }

  // Return only tags that exist on this product AND are relevant to the query
  return contextualTags.filter(tag => relevantTags.has(tag));
}
```

**Step 3 — Render pills in the search dropdown**

For each product result in the dropdown, render matching tags as small pills below the product title/category. Limit to max 3 pills to keep it clean.

```html
<!-- Inside each search result item -->
<div class="search-result-item">
  <img src="..." class="search-result-thumb" />
  <div class="search-result-info">
    <span class="search-result-title">Bermuda Grass Seed Mix for Lawns</span>
    <span class="search-result-price">$119.99 – $499.99</span>
    <span class="search-result-category">Lawn Seed</span>

    <!-- NEW: Contextual tag pills -->
    <div class="search-result-tags">
      <span class="search-tag-pill">Drought Tolerant</span>
      <span class="search-tag-pill">Lawn Seed</span>
    </div>
  </div>
</div>
```

**Step 4 — Style the pills**

```css
.search-result-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.search-tag-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  line-height: 1.4;
  white-space: nowrap;
  background-color: #f0f5f0;  /* Light sage green — matches NS brand */
  color: #3d6b3d;
  border: 1px solid #d4e5d4;
}

/* Optional: Different colors for different tag types */
.search-tag-pill[data-type="animal"] {
  background-color: #faf3eb;
  color: #8b6914;
  border-color: #e8d5b0;
}
```

### Visual example (ASCII mockup)

```
┌──────────────────────────────────────────────┐
│ 🔍 drought tolerant lawn                    x│
├──────────────────────────────────────────────┤
│  PRODUCTS                                    │
│                                              │
│  [img] Bermuda Grass Seed Mix for Lawns      │
│        $119.99 – $499.99                     │
│        Lawn Seed                             │
│        [Drought Tolerant] [Lawn Seed]        │ ← pills
│                                              │
│  [img] Sheep Fescue Grass Seed               │
│        $39.99 – $149.99                      │
│        Lawn Seed                             │
│        [Drought Tolerant] [Lawn Alternative] │ ← pills
│                                              │
│  [img] Sundancer Buffalograss Lawn Seed      │
│        $116.99 – $496.99                     │
│        Lawn Seed                             │
│        [Drought Tolerant] [Lawn Seed]        │ ← pills
└──────────────────────────────────────────────┘
```

### Important notes
- Only show pills when they match the search query. For a plain "bermuda" search, don't show tags.
- Cap at 3 pills max per result to avoid visual clutter.
- If no tags match the query, don't render the `.search-result-tags` div at all.
- The `contextual_tags` field is already indexed and facetable. No Algolia config changes needed.

---

## Feature 2: "We Don't Carry This" Redirect Messages

### What it does
When a customer searches for a product we don't carry (e.g., "zoysia", "sorghum", "creeping thyme"), instead of showing 0 results, we show related products from the same category with a friendly message:

> "We don't carry Zoysia grass seed this season. Here are other warm-season lawn grasses that might interest you:"

### Data available
Algolia Rules are already configured. When a no-catalog query fires, the API response includes a `userData` array with the redirect message:

```json
{
  "hits": [ /* redirected results */ ],
  "userData": [
    {
      "message": "We don't carry Zoysia grass seed this season. Here are other warm-season lawn grasses that might interest you:",
      "originalQuery": "zoysia"
    }
  ]
}
```

### Currently covered queries (17 redirects)

| Search query | Redirected to | Searches/period |
|---|---|---|
| zoysia / zoysiagrass | Warm season lawn | 19+ |
| sorghum | Cover crop/forage | 11+ |
| creeping thyme | Lawn alternative ground cover | 11+ |
| centipede | Warm season lawn | 6 |
| dandelion | Wildflower/pollinator | 8 |
| cosmos | Wildflower | 6 |
| zinnias | Wildflower | 5 |
| dichondra | Lawn alternative ground cover | 4 |
| hibiscus | Wildflower | 3 |
| marigold | Wildflower | 3 |
| nasturtium | Wildflower/pollinator | 2 |
| crabgrass | Warm season lawn | 5 |
| cat grass | Forage | 2 |
| tobacco | Cover crop | 2 |
| kurapia | Lawn alternative ground cover | 2 |
| comfrey | Cover crop/nitrogen | 3 |
| thyme (exact) | Lawn alternative ground cover | 10 |

### How to implement

**Step 1 — Check for `userData` in the Algolia response**

After receiving the search response, check if `userData` exists and has a message:

```js
function handleSearchResponse(response) {
  const { hits, userData } = response;

  // Check for no-catalog redirect message
  if (userData && userData.length > 0 && userData[0].message) {
    renderRedirectMessage(userData[0].message);
  } else {
    hideRedirectMessage();
  }

  // Render hits as normal
  renderSearchResults(hits);
}
```

**Step 2 — Render the redirect message banner**

Add a message banner above the product results in the search dropdown:

```html
<!-- Inside search dropdown, above PRODUCTS section -->
<div class="search-redirect-banner" id="searchRedirectBanner" style="display: none;">
  <svg class="redirect-icon" width="16" height="16" viewBox="0 0 16 16">
    <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.5"/>
    <path d="M8 5v3M8 10.5v.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </svg>
  <span class="redirect-message" id="redirectMessageText"></span>
</div>
```

```js
function renderRedirectMessage(message) {
  const banner = document.getElementById('searchRedirectBanner');
  const text = document.getElementById('redirectMessageText');
  text.textContent = message;
  banner.style.display = 'flex';
}

function hideRedirectMessage() {
  const banner = document.getElementById('searchRedirectBanner');
  if (banner) banner.style.display = 'none';
}
```

**Step 3 — Style the banner**

```css
.search-redirect-banner {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 16px;
  margin: 0 0 8px 0;
  background-color: #fef9f0;      /* Warm cream */
  border-bottom: 1px solid #e8dcc8;
  font-size: 13px;
  line-height: 1.4;
  color: #6b5b3e;
}

.redirect-icon {
  flex-shrink: 0;
  margin-top: 1px;
  color: #c4943a;                 /* NS brand amber accent */
}

.redirect-message {
  flex: 1;
}
```

### Visual example (ASCII mockup)

```
┌──────────────────────────────────────────────┐
│ 🔍 zoysia                                  x│
├──────────────────────────────────────────────┤
│ ⓘ We don't carry Zoysia grass seed this     │ ← banner
│   season. Here are other warm-season lawn    │
│   grasses that might interest you:           │
├──────────────────────────────────────────────┤
│  PRODUCTS                                    │
│                                              │
│  [img] Bermuda Grass Seed Mix for Lawns      │
│        $119.99 – $499.99                     │
│        Lawn Seed                             │
│        [Drought Tolerant] [Lawn Seed]        │
│                                              │
│  [img] Sundancer Buffalograss Lawn Seed      │
│        $116.99 – $496.99                     │
│        Lawn Seed                             │
│        [Drought Tolerant] [Lawn Seed]        │
│                                              │
│  [img] Perennial Ryegrass Seed Mix           │
│        $26.99 – $109.99                      │
│        Lawn Seed                             │
│        [Lawn Seed] [Sports Turf]             │
└──────────────────────────────────────────────┘
```

### Important notes
- `userData` only appears when a no-catalog redirect rule fires. Normal searches will have `userData: undefined` or empty.
- The message text is fully controlled from Algolia — no need to hardcode messages in the frontend. New redirects can be added without code changes.
- The `originalQuery` field in userData can be used for analytics tracking (e.g., log that customer searched for "zoysia" but was redirected).

---

## Feature 3 (Bonus): Enable Click Analytics

### What it does
Sends click position data back to Algolia so we can track which results customers actually click on, and Algolia can use this to improve relevance over time.

### How to implement

**Step 1 — Add `clickAnalytics: true` to the query params**

In the Algolia search query, add:

```js
{
  query: searchText,
  hitsPerPage: 5,
  clickAnalytics: true,   // ADD THIS
  // ... rest of params
}
```

**Step 2 — Send click events**

When a user clicks a product result, send a `clickedObjectIDsAfterSearch` event:

```js
function onSearchResultClick(hit, position, queryID) {
  // queryID comes from the search response when clickAnalytics is enabled
  fetch(`https://insights.algolia.io/1/events`, {
    method: 'POST',
    headers: {
      'X-Algolia-Application-Id': 'CR7906DEBT',
      'X-Algolia-API-Key': 'e873ad4081aaea5a24e840ff99a13e51',  // search key is fine
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      events: [{
        eventType: 'click',
        eventName: 'Product Clicked',
        index: 'wp_prod_posts_product',
        userToken: getUserToken(),  // anonymous session ID
        queryID: queryID,
        objectIDs: [hit.objectID],
        positions: [position],  // 1-indexed position in results
        timestamp: Date.now(),
      }]
    })
  });
}
```

The `queryID` is automatically included in the search response when `clickAnalytics: true`.

---

## Summary of Algolia fields available

| Field | Type | Purpose |
|---|---|---|
| `contextual_tags` | `string[]` | Array of contextual labels like "Drought Tolerant", "Attracts Pollinators", "Cattle Forage" |
| `userData` | `object[]` | Present in response when a no-catalog redirect rule fires. Contains `.message` and `.originalQuery` |
| `queryID` | `string` | Present in response when `clickAnalytics: true`. Used for click event tracking |

All 37 possible tag values:

```
Drought Tolerant, Attracts Pollinators, Erosion Control, Pet Friendly,
Shade Tolerant, Full Sun, Native Species, California Native,
Wildlife Habitat, Nitrogen Fixing, Lawn Alternative, Sports Turf,
Hay Production, Forage & Grazing, Food Plot, Cover Crop,
Ornamental, Meadow, Slopes & Hillsides, Low Maintenance,
Regular Water, Moderate Water, Low to Moderate Water,
Perennial, Annual, Lawn Seed, Water-Wise, Clover,
Cattle Forage, Sheep Forage, Goat Forage, Horse Forage,
Bison Forage, Alpaca & Llama Forage, Poultry Forage,
Pig Forage, Tortoise Forage
```
