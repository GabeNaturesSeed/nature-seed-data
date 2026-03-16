#!/bin/bash
# ─── Algolia Enrichment Cron ──────────────────────────────────────────
# Re-enriches Algolia product records with WooCommerce data.
# Designed to run on a schedule to recover enrichments after WP plugin
# overwrites records on product save.
#
# Install:
#   crontab -e
#   # Run every 6 hours:
#   0 */6 * * * "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/algolia-optimization/cron_enrich.sh" >> "/Users/gabegimenes-silva/Desktop/ClaudeDataAgent -/algolia-optimization/data/cron.log" 2>&1
#
# ──────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/data/cron.log"
PYTHON="/usr/bin/python3"

# Ensure data dir exists
mkdir -p "$SCRIPT_DIR/data"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  Algolia Enrichment Cron — $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════════"

# Step 1: Content + SKU enrichment
echo ""
echo "  [1/2] Running content enrichment..."
$PYTHON "$SCRIPT_DIR/enrich_records.py" --push

# Step 2: Contextual tags
echo ""
echo "  [2/3] Running contextual tags..."
$PYTHON "$SCRIPT_DIR/add_contextual_tags.py" --push

# Step 3: Auto-synonym review (daily — finds and fixes no-result queries)
echo ""
echo "  [3/3] Running auto-synonym review..."
$PYTHON "$SCRIPT_DIR/auto_synonym_review.py" --push

echo ""
echo "  Cron complete — $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════════"
