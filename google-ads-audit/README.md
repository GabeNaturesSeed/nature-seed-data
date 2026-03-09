# Google Ads 4-Year Data Extraction & Audit

Complete account audit spanning March 2022 – March 2026. Uses Google Ads Scripts (run inside the Google Ads UI) to export data to Google Sheets, then a Python normalization pipeline maps historical products to current SKUs.

## Quick Start

### Step 1: Create Google Sheet
1. Create a new Google Sheet
2. Copy the URL (e.g., `https://docs.google.com/spreadsheets/d/ABC123/edit`)

### Step 2: Run Scripts 1 & 8 First (structural data)
1. Go to **Google Ads > Tools & Settings > Bulk Actions > Scripts**
2. Click **+ New Script**
3. Open `scripts/01_campaign_structure.js`, paste the Google Sheet URL in the `SPREADSHEET_URL` config
4. Paste the script and click **Run** (or Preview first)
5. Repeat with `scripts/08_conversions_setup.js`
6. **Verify:** Check the Google Sheet — you should see `Campaigns_Structure` and `Conversions_Setup` tabs

### Step 3: Run Scripts 2–7 (performance data)
Run these sequentially (each reuses the same Sheet URL):

| Order | Script | Tab(s) Created | Est. Time |
|-------|--------|----------------|-----------|
| 1 | `02_monthly_campaign_perf.js` | `Monthly_Campaign_Perf` | 10-15 min |
| 2 | `03_adgroups_keywords.js` | `AdGroups_Keywords` | 15-25 min |
| 3 | `04_search_terms.js` | `Search_Terms` | 15-25 min |
| 4 | `05_shopping_products.js` | `Shopping_Products` | 10-20 min |
| 5 | `06_ad_copy_perf.js` | `Ad_Copy_Perf` | 5-10 min |
| 6 | `07_audience_geo_device.js` | `Geo_State_Perf` + `Device_Perf` | 10-15 min |

**Total estimated time: ~1.5–2 hours**

### Step 4: Export to CSV
1. In Google Sheets, go to **File > Download > Comma Separated Values (.csv)**
2. Or download individual tabs: right-click tab > Download as CSV
3. Place all CSVs in the `data/` directory with these exact names:
   - `Campaigns_Structure.csv`
   - `Monthly_Campaign_Perf.csv`
   - `AdGroups_Keywords.csv`
   - `Search_Terms.csv`
   - `Shopping_Products.csv`
   - `Ad_Copy_Perf.csv`
   - `Geo_State_Perf.csv`
   - `Device_Perf.csv`
   - `Conversions_Setup.csv`
   - `Conversions_Volume_Summary.csv`

### Step 5: Run Normalization Pipeline
```bash
cd google-ads-audit
python normalize_google_ads.py
```

Or dry-run first to check data loading:
```bash
python normalize_google_ads.py --dry-run
```

## Output Files
| File | Description |
|------|-------------|
| `unified_4yr_performance.csv` | Shopping products matched to current SKUs |
| `sku_normalization_report.csv` | Audit trail: how each product was matched |
| `unmatched_products.csv` | Products needing manual SKU mapping |
| `category_performance_summary.csv` | Monthly performance by product category |
| `campaign_category_map.csv` | Each campaign tagged with inferred category |

## Troubleshooting

### Script times out (30-min limit)
- **Search Terms (Script 4):** Set `CLICKS_THRESHOLD` to `1` or higher in the config
- **Keywords (Script 3):** Already batches by year; if still timing out, reduce year ranges to 6-month chunks

### "Exceeded maximum execution time"
The script ran over 30 minutes. Split the `YEAR_RANGES` into smaller chunks (e.g., 6-month periods instead of full years).

### Empty tabs
Check that the date range covers dates when the campaign type was active. Shopping campaigns may not exist for all 4 years.

### Google Sheets row limit (10M cells)
If any tab exceeds limits, the script will error on write. Increase `CLICKS_THRESHOLD` or narrow date ranges.

## File Structure
```
google-ads-audit/
├── scripts/
│   ├── 01_campaign_structure.js      # All campaigns (active/paused/removed)
│   ├── 02_monthly_campaign_perf.js   # Monthly metrics per campaign
│   ├── 03_adgroups_keywords.js       # Keyword-level performance + quality score
│   ├── 04_search_terms.js            # User search queries
│   ├── 05_shopping_products.js       # Product-level Shopping/PMax data
│   ├── 06_ad_copy_perf.js            # Ad headlines, descriptions, CTR
│   ├── 07_audience_geo_device.js     # State geo + device breakdown
│   └── 08_conversions_setup.js       # Conversion actions + volume summary
├── data/                              # Drop exported CSVs here
├── normalize_google_ads.py           # Python normalization pipeline
└── README.md
```
