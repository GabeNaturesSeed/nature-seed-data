"""
SEO Article Creation App — Nature's Seed

Flask server that orchestrates keyword research, article drafting,
media management, and WordPress publishing.

Usage:
    cd seo-article-app
    pip install -r requirements.txt
    python app.py
"""

import os
import json
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import load_dotenv

# Load .env from parent directory (nature-seed-data/.env)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from research import run_full_research, CONTENT_VERTICALS
from drafting import generate_article_draft, refine_article, generate_outline
from wp_client import (
    search_media, get_products, get_categories, get_product_by_slug,
    create_post, update_post, get_posts,
)
from interactives import (
    build_product_card, build_comparison_table, build_seeding_calculator,
    build_zone_map, build_faq_schema, build_callout_box, build_table_of_contents,
)

app = Flask(__name__)

# In-memory draft storage (would use a DB in production)
DRAFTS = {}
DRAFT_COUNTER = 0


# ── Pages ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Research API ──────────────────────────────────────────────────────

@app.route("/api/research", methods=["GET"])
def api_research():
    """Run keyword research and return topic suggestions."""
    results = run_full_research()
    return jsonify(results)


@app.route("/api/verticals", methods=["GET"])
def api_verticals():
    """Return product verticals with seed keywords."""
    return jsonify(CONTENT_VERTICALS)


# ── Drafting API ──────────────────────────────────────────────────────

@app.route("/api/outline", methods=["POST"])
def api_outline():
    """Generate an article outline before full draft."""
    data = request.json
    topic = data.get("topic", "")
    keywords = data.get("keywords", [])
    if not topic:
        return jsonify({"error": "topic is required"}), 400
    outline = generate_outline(topic, keywords)
    return jsonify(outline)


@app.route("/api/draft", methods=["POST"])
def api_draft():
    """Generate a full article draft."""
    global DRAFT_COUNTER
    data = request.json
    topic = data.get("topic", "")
    keywords = data.get("keywords", [])
    vertical = data.get("vertical", "")
    custom_instructions = data.get("instructions", "")

    if not topic:
        return jsonify({"error": "topic is required"}), 400

    # Fetch relevant products for the vertical
    products = []
    if vertical and vertical in CONTENT_VERTICALS:
        cat_ids = CONTENT_VERTICALS[vertical]["category_ids"]
        for cat_id in cat_ids[:2]:
            try:
                prods = get_products(category_id=cat_id, per_page=10)
                products.extend(prods)
            except Exception:
                pass

    article = generate_article_draft(
        topic=topic,
        keywords=keywords,
        vertical=vertical,
        products=products,
        custom_instructions=custom_instructions,
    )

    # Store draft
    DRAFT_COUNTER += 1
    draft_id = f"draft_{DRAFT_COUNTER}"
    article["draft_id"] = draft_id
    article["status"] = "draft"
    article["created_at"] = datetime.now().isoformat()
    article["vertical"] = vertical
    DRAFTS[draft_id] = article

    return jsonify(article)


@app.route("/api/draft/<draft_id>", methods=["GET"])
def api_get_draft(draft_id):
    """Get a specific draft."""
    draft = DRAFTS.get(draft_id)
    if not draft:
        return jsonify({"error": "Draft not found"}), 404
    return jsonify(draft)


@app.route("/api/draft/<draft_id>", methods=["PUT"])
def api_update_draft(draft_id):
    """Update a draft (from editor)."""
    draft = DRAFTS.get(draft_id)
    if not draft:
        return jsonify({"error": "Draft not found"}), 404

    data = request.json
    for key in ["title", "content", "meta_description", "slug", "status"]:
        if key in data:
            draft[key] = data[key]
    draft["updated_at"] = datetime.now().isoformat()

    return jsonify(draft)


@app.route("/api/draft/<draft_id>/refine", methods=["POST"])
def api_refine_draft(draft_id):
    """Refine a draft with AI based on feedback."""
    draft = DRAFTS.get(draft_id)
    if not draft:
        return jsonify({"error": "Draft not found"}), 404

    data = request.json
    feedback = data.get("feedback", "")
    if not feedback:
        return jsonify({"error": "feedback is required"}), 400

    refined = refine_article(json.dumps(draft), feedback)
    # Merge refined content into draft
    for key in ["title", "content", "meta_description", "faq", "internal_links", "image_suggestions"]:
        if key in refined:
            draft[key] = refined[key]
    draft["updated_at"] = datetime.now().isoformat()

    return jsonify(draft)


@app.route("/api/drafts", methods=["GET"])
def api_list_drafts():
    """List all drafts."""
    drafts = sorted(DRAFTS.values(), key=lambda d: d.get("created_at", ""), reverse=True)
    # Return summary only
    summaries = []
    for d in drafts:
        summaries.append({
            "draft_id": d["draft_id"],
            "title": d.get("title", "Untitled"),
            "status": d.get("status", "draft"),
            "vertical": d.get("vertical", ""),
            "created_at": d.get("created_at", ""),
            "updated_at": d.get("updated_at", ""),
        })
    return jsonify(summaries)


# ── Media API ─────────────────────────────────────────────────────────

@app.route("/api/media/search", methods=["GET"])
def api_media_search():
    """Search WordPress media library by alt text / title."""
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "q parameter required"}), 400
    results = search_media(query)
    return jsonify(results)


# ── Interactive Elements API ──────────────────────────────────────────

@app.route("/api/interactive/product-card", methods=["POST"])
def api_product_card():
    """Generate a product card for a given product slug."""
    data = request.json
    slug = data.get("slug", "")
    if not slug:
        return jsonify({"error": "slug required"}), 400

    product = get_product_by_slug(slug)
    if not product:
        return jsonify({"error": f"Product '{slug}' not found"}), 404

    html = build_product_card(product)
    return jsonify({"html": html, "product_name": product["name"]})


@app.route("/api/interactive/calculator", methods=["GET"])
def api_calculator():
    """Get seeding rate calculator widget HTML."""
    return jsonify({"html": build_seeding_calculator()})


@app.route("/api/interactive/zone-map", methods=["GET"])
def api_zone_map():
    """Get zone finder widget HTML."""
    return jsonify({"html": build_zone_map()})


@app.route("/api/interactive/faq", methods=["POST"])
def api_faq():
    """Generate FAQ section with schema markup."""
    data = request.json
    faqs = data.get("faqs", [])
    if not faqs:
        return jsonify({"error": "faqs array required"}), 400
    html = build_faq_schema(faqs)
    return jsonify({"html": html})


@app.route("/api/interactive/comparison-table", methods=["POST"])
def api_comparison_table():
    """Generate a comparison table."""
    data = request.json
    items = data.get("items", [])
    columns = data.get("columns", [])
    if not items or not columns:
        return jsonify({"error": "items and columns required"}), 400
    html = build_comparison_table(items, columns)
    return jsonify({"html": html})


@app.route("/api/interactive/callout", methods=["POST"])
def api_callout():
    """Generate a callout/tip box."""
    data = request.json
    text = data.get("text", "")
    box_type = data.get("type", "tip")
    if not text:
        return jsonify({"error": "text required"}), 400
    html = build_callout_box(text, box_type)
    return jsonify({"html": html})


@app.route("/api/interactive/toc", methods=["POST"])
def api_toc():
    """Generate table of contents from headings."""
    data = request.json
    headings = data.get("headings", [])
    if not headings:
        return jsonify({"error": "headings array required"}), 400
    html = build_table_of_contents(headings)
    return jsonify({"html": html})


# ── Publishing API ────────────────────────────────────────────────────

@app.route("/api/publish/<draft_id>", methods=["POST"])
def api_publish(draft_id):
    """Publish a draft to WordPress."""
    draft = DRAFTS.get(draft_id)
    if not draft:
        return jsonify({"error": "Draft not found"}), 404

    data = request.json or {}
    status = data.get("status", "draft")  # draft or publish

    # Process content: resolve image placeholders
    content = draft.get("content", "")
    content = _resolve_image_placeholders(content)

    # Add FAQ schema if present
    if draft.get("faq"):
        content += "\n" + build_faq_schema(draft["faq"])

    # Build post data
    categories = data.get("categories", [])
    tags = data.get("tags", [])
    featured_media = data.get("featured_media")

    # SEO meta (for Yoast/RankMath)
    meta = {}
    if draft.get("meta_description"):
        meta["_yoast_wpseo_metadesc"] = draft["meta_description"]
        meta["rank_math_description"] = draft["meta_description"]
    if draft.get("primary_keyword"):
        meta["_yoast_wpseo_focuskw"] = draft["primary_keyword"]
        meta["rank_math_focus_keyword"] = draft["primary_keyword"]

    try:
        result = create_post(
            title=draft.get("title", "Untitled"),
            content=content,
            status=status,
            categories=categories,
            tags=tags,
            featured_media=featured_media,
            meta=meta if meta else None,
        )
        draft["status"] = "published"
        draft["wp_post_id"] = result.get("id")
        draft["wp_url"] = result.get("link")
        draft["published_at"] = datetime.now().isoformat()

        return jsonify({
            "success": True,
            "post_id": result.get("id"),
            "url": result.get("link"),
            "status": result.get("status"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _resolve_image_placeholders(content):
    """Find [IMAGE: alt text] placeholders and replace with actual WP media."""
    pattern = r'\[IMAGE:\s*(.+?)\]'
    matches = re.findall(pattern, content)

    for alt_text in matches:
        try:
            results = search_media(alt_text)
            if results:
                img = results[0]
                img_url = img.get("medium") or img.get("url", "")
                img_html = f'<figure style="margin:24px 0;"><img src="{img_url}" alt="{alt_text}" loading="lazy" style="width:100%;border-radius:8px;"/><figcaption style="text-align:center;color:#666;font-size:14px;margin-top:8px;">{alt_text}</figcaption></figure>'
                content = content.replace(f"[IMAGE: {alt_text}]", img_html)
        except Exception:
            # Leave placeholder if media search fails
            pass

    return content


# ── Products API (for editor) ────────────────────────────────────────

@app.route("/api/products", methods=["GET"])
def api_products():
    """Search/list products for inserting into articles."""
    search = request.args.get("search", "")
    category = request.args.get("category", "")
    params = {"status": "publish", "per_page": 20}
    if search:
        params["search"] = search
    if category:
        params["category"] = category

    try:
        from wp_client import wc_get
        products, _ = wc_get("products", params)
        # Return slim product data
        slim = []
        for p in products:
            slim.append({
                "id": p["id"],
                "name": p["name"],
                "slug": p["slug"],
                "price": p.get("price", ""),
                "image": p["images"][0]["src"] if p.get("images") else "",
                "short_description": p.get("short_description", "")[:150],
                "categories": [c["name"] for c in p.get("categories", [])],
            })
        return jsonify(slim)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/categories", methods=["GET"])
def api_categories():
    """List product categories."""
    try:
        cats = get_categories()
        slim = [{"id": c["id"], "name": c["name"], "slug": c["slug"], "count": c.get("count", 0)} for c in cats]
        return jsonify(slim)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
