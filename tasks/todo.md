# SEO Article Creation App — Nature's Seed

## Plan

### Architecture
- **Backend**: Python Flask API server
- **Frontend**: Single-page HTML app with rich text editor (Quill.js)
- **WordPress**: REST API v2 for posts + media (through CF Worker proxy for reads, direct for writes)
- **AI**: Claude API for keyword research analysis + article drafting

### Components

1. [ ] **Keyword Research Engine** (`research.py`)
   - Pull top queries from Google Search Console API
   - Analyze existing WooCommerce product categories for content gaps
   - Score keywords by intent (commercial > informational) and difficulty
   - Suggest article topics with target keywords, search volume signals

2. [ ] **Article Draft Generator** (`drafting.py`)
   - Use Claude API to generate SEO-optimized article drafts
   - Structure: H1, meta description, H2/H3 outline, internal links, product mentions
   - Auto-link to Nature's Seed products where relevant
   - Include placeholder alt-text tags for image insertion

3. [ ] **WordPress Media Finder** (`wp_media.py`)
   - Search WP media library by alt text via REST API
   - Return matching images with URLs for insertion into articles
   - Fall back to product images from WooCommerce if no media match

4. [ ] **Interactive Element Builder** (`interactives.py`)
   - Generate shortcodes/HTML for: planting calculators, comparison tables, zone maps
   - Embed product cards (existing pattern from search-console work)
   - FAQ schema markup (structured data for SEO)

5. [ ] **Flask API Server** (`app.py`)
   - `GET /api/research` — Run keyword research, return topic suggestions
   - `GET /api/research/{topic}` — Deep dive on a specific topic
   - `POST /api/draft` — Generate article draft from topic + keywords
   - `GET /api/media/search?alt={text}` — Search WP media
   - `POST /api/publish` — Publish approved article to WordPress
   - `GET /api/articles` — List draft/published articles

6. [ ] **Front-end Editor** (`templates/index.html`)
   - Topic research dashboard with keyword scores
   - Rich text editor (Quill.js) for reviewing/editing drafts
   - Image picker panel (searches WP media by alt text)
   - Interactive element inserter
   - One-click publish with preview

7. [ ] **WordPress Publisher** (`publisher.py`)
   - Create post via WP REST API (`/wp-json/wp/v2/posts`)
   - Set category, tags, featured image, SEO meta (Yoast/RankMath)
   - Publish as "Resource" post type or standard post
   - Handle image attachment and alt text

### File Structure
```
seo-article-app/
├── app.py                 # Flask server
├── research.py            # Keyword research engine
├── drafting.py            # Claude API article generator
├── wp_media.py            # WordPress media search
├── wp_client.py           # WordPress REST API client
├── publisher.py           # Article publisher
├── interactives.py        # Interactive element builder
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Front-end editor SPA
└── README.md              # Setup & usage guide
```

## Implementation Progress
- [x] Build WordPress REST API client (posts + media) — `wp_client.py`
- [x] Build keyword research engine — `research.py`
- [x] Build article draft generator with Claude API — `drafting.py`
- [x] Build interactive element builder — `interactives.py`
- [x] Build Flask API server — `app.py` (20 endpoints)
- [x] Build front-end editor UI — `templates/index.html` (Quill.js editor)
- [x] Build publisher module — integrated in `app.py` + `wp_client.py`
- [x] Integration test — all endpoints verified

## Setup Requirements
Add these to `.env`:
- `ANTHROPIC_API_KEY` — for Claude article drafting
- `WP_APP_USER` — WordPress application username
- `WP_APP_PASSWORD` — WordPress application password (generate in WP admin → Users → Application Passwords)
- Existing `WC_CK`, `WC_CS` — already set for product data
- Existing Google OAuth tokens — already set for Search Console research
