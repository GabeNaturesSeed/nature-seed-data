"""
Marketplace Management Bot — Nature's Seed
==========================================
Runs every Tuesday and Friday via GitHub Actions.

Workflow:
    1. Pull last 7 days of Amazon SP-API data (orders, revenue)
    2. Pull last 7 days of Walmart Marketplace data (orders, items)
    3. Analyze both → generate URGENT / ACTION / INFO findings
    4. Send structured report to Telegram
    5. Run approval flow for 🟡 ACTION items
    6. Log approved actions to action_log.md for manual execution

Note: This bot does NOT execute marketplace changes directly.
      Approved actions are logged as a to-do list for Seller Central / Walmart Seller Center.
"""

import json
import logging
import time
import uuid
import base64
import urllib.request
import urllib.parse
import urllib.error
import requests
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("marketplace_bot")

# ── Paths ─────────────────────────────────────────────────────────────────────

BOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BOT_DIR.parent
ACTION_LOG_PATH = BOT_DIR / "action_log.md"

# ── Telegram Constants ────────────────────────────────────────────────────────

MAX_LEN = 4096
POLL_INTERVAL = 10       # seconds between Telegram polls
APPROVAL_TIMEOUT = 300   # 5 minutes

# ── .env Loading ──────────────────────────────────────────────────────────────

def _load_env() -> dict:
    """
    Parse .env from project root.
    Handles spaces around '=' and quoted values:
        AMAZON_CLIENT_ID = 'abc123'   →   {'AMAZON_CLIENT_ID': 'abc123'}
    """
    env_path = PROJECT_ROOT / ".env"
    env_vars = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip().strip("'\"")
    return env_vars


# ── Telegram Helpers ──────────────────────────────────────────────────────────

def _tg_api(token: str, method: str, data: dict) -> dict:
    """Make a single Telegram Bot API call. Retries once on rate-limit."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code == 429:
            retry_after = json.loads(body).get("parameters", {}).get("retry_after", 5)
            log.info(f"Telegram rate-limited — waiting {retry_after}s")
            time.sleep(retry_after)
            return _tg_api(token, method, data)
        log.error(f"Telegram API error {e.code}: {body}")
        raise


def _split_text(text: str) -> list:
    """Split text into chunks that fit within Telegram's 4096-char limit."""
    if len(text) <= MAX_LEN:
        return [text]
    chunks = []
    current = ""
    for line in text.split("\n"):
        candidate = (current + "\n" + line) if current else line
        if len(candidate) > MAX_LEN:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def send_telegram(token: str, chat_id: str, text: str) -> None:
    """Send a message to Telegram, splitting into chunks if needed."""
    for i, chunk in enumerate(_split_text(text)):
        _tg_api(token, "sendMessage", {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        })
        if i > 0:
            time.sleep(0.2)


def poll_telegram(token: str, chat_id: str, timeout_seconds: int = APPROVAL_TIMEOUT):
    """
    Poll Telegram for a reply from the expected chat.

    Clears stale updates first, then polls every POLL_INTERVAL seconds until
    a message arrives from chat_id or timeout is reached.

    Returns the message text, or None on timeout.
    """
    log.info(f"Polling for Telegram reply (timeout: {timeout_seconds}s)...")

    # Clear stale updates so we only get replies sent AFTER this point
    stale = _tg_api(token, "getUpdates", {"offset": 0, "timeout": 0})
    offset = 0
    if stale.get("result"):
        offset = stale["result"][-1]["update_id"] + 1

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        remaining = deadline - time.time()
        poll_timeout = min(30, int(remaining))
        if poll_timeout <= 0:
            break

        try:
            result = _tg_api(token, "getUpdates", {
                "offset": offset,
                "timeout": poll_timeout,
                "allowed_updates": ["message"],
            })
        except Exception as e:
            log.warning(f"Poll error (will retry): {e}")
            time.sleep(POLL_INTERVAL)
            continue

        for update in result.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            text = msg.get("text", "").strip()
            msg_chat_id = str(msg.get("chat", {}).get("id", ""))
            if msg_chat_id == str(chat_id) and text:
                log.info(f"Got reply: {text!r}")
                return text

        time.sleep(POLL_INTERVAL)

    log.warning("Poll timeout — no reply received")
    return None


# ── Amazon SP-API ─────────────────────────────────────────────────────────────

def _amz_get_token(env_vars: dict) -> str:
    """Exchange Amazon refresh token for a fresh access token."""
    resp = requests.post(
        "https://api.amazon.com/auth/o2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": env_vars["AMAZON_REFRESH_TOKEN"],
            "client_id": env_vars["AMAZON_CLIENT_ID"],
            "client_secret": env_vars["AMAZON_CLIENT_SECRET"],
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _amz_get_orders(token: str, created_after: str, created_before: str) -> list:
    """
    Fetch all orders from the Amazon Orders API for the given date range.
    Paginates automatically. Returns flat list of order dicts.
    created_after / created_before must be ISO-8601 UTC strings (e.g. '2026-03-04T00:00:00Z').
    """
    base_url = "https://sellingpartnerapi-na.amazon.com/orders/v0/orders"
    headers = {"x-amz-access-token": token}
    params = {
        "MarketplaceIds": "ATVPDKIKX0DER",
        "CreatedAfter": created_after,
        "CreatedBefore": created_before,
        "MaxResultsPerPage": 100,
    }

    orders = []
    next_token = None

    while True:
        if next_token:
            p = {"NextToken": next_token}
        else:
            p = params

        resp = requests.get(base_url, headers=headers, params=p, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        payload = data.get("payload", {})
        orders.extend(payload.get("Orders", []))
        next_token = payload.get("NextToken")

        if not next_token:
            break

        time.sleep(0.5)

    return orders


def pull_amazon_data(env_vars: dict) -> dict:
    """
    Pull 14 days of Amazon orders so we can compare last 7 vs prior 7.
    Returns dict with 'current_orders', 'prior_orders', 'error'.
    """
    try:
        token = _amz_get_token(env_vars)
    except Exception as e:
        return {"error": f"Auth failed: {e}", "current_orders": [], "prior_orders": []}

    today_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    seven_ago = today_utc - timedelta(days=7)
    fourteen_ago = today_utc - timedelta(days=14)

    fmt = "%Y-%m-%dT%H:%M:%SZ"
    today_str = today_utc.strftime(fmt)
    seven_str = seven_ago.strftime(fmt)
    fourteen_str = fourteen_ago.strftime(fmt)

    try:
        current_orders = _amz_get_orders(token, seven_str, today_str)
    except Exception as e:
        return {"error": f"Orders fetch failed: {e}", "current_orders": [], "prior_orders": []}

    try:
        prior_orders = _amz_get_orders(token, fourteen_str, seven_str)
    except Exception as e:
        log.warning(f"Could not fetch prior-week Amazon orders: {e}")
        prior_orders = []

    return {
        "error": None,
        "current_orders": current_orders,
        "prior_orders": prior_orders,
        "date_range": f"{seven_str} → {today_str}",
    }


def _amz_order_revenue(order: dict) -> float:
    """Extract order total from an Amazon order. Returns 0 for Pending orders."""
    if order.get("OrderStatus") == "Pending":
        return 0.0
    amount = order.get("OrderTotal", {}).get("Amount", "0")
    try:
        return float(amount)
    except (ValueError, TypeError):
        return 0.0


def _amz_top_products(orders: list, n: int = 3) -> list:
    """
    Identify top N products by revenue from order list.
    Uses OrderItems endpoint if available; falls back to order-level data.
    Returns list of dicts: {name, revenue, orders}.
    """
    # Group by ASIN from order items if present, else use product_name from order
    product_rev = {}   # asin/name → total revenue
    product_cnt = {}   # asin/name → order count

    for order in orders:
        rev = _amz_order_revenue(order)
        if rev == 0:
            continue
        # SP-API Orders list endpoint doesn't return line items — use order-level product name
        # The order object has no line items at this endpoint; we approximate by order
        name = order.get("SellerOrderId") or order.get("AmazonOrderId", "Unknown")
        # Try to get a product name from any available field
        product_name = "Amazon Order"  # default label — line items require a separate API call
        product_rev[product_name] = product_rev.get(product_name, 0.0) + rev
        product_cnt[product_name] = product_cnt.get(product_name, 0) + 1

    results = [
        {"name": name, "revenue": rev, "orders": product_cnt.get(name, 0)}
        for name, rev in sorted(product_rev.items(), key=lambda x: -x[1])
    ]
    return results[:n]


def analyze_amazon(data: dict) -> dict:
    """
    Analyze Amazon pull data and return structured findings.
    Returns: {revenue, orders, aov, prior_revenue, pct_change, pending_count,
              top_products, urgents, actions, infos}
    """
    urgents = []
    actions = []
    infos = []

    if data.get("error"):
        return {
            "error": data["error"],
            "revenue": 0,
            "orders": 0,
            "aov": 0,
            "prior_revenue": 0,
            "pct_change": None,
            "pending_count": 0,
            "top_products": [],
            "urgents": [],
            "actions": [{"platform": "Amazon", "text": f"Could not pull Amazon data: {data['error']}"}],
            "infos": [],
        }

    current = data.get("current_orders", [])
    prior = data.get("prior_orders", [])

    # Revenue (exclude Pending)
    current_rev = sum(_amz_order_revenue(o) for o in current)
    prior_rev = sum(_amz_order_revenue(o) for o in prior)
    order_count = len(current)
    pending_count = sum(1 for o in current if o.get("OrderStatus") == "Pending")
    non_pending_count = order_count - pending_count
    aov = (current_rev / non_pending_count) if non_pending_count > 0 else 0.0

    # Compare to prior week
    pct_change = None
    if prior_rev > 0:
        pct_change = ((current_rev - prior_rev) / prior_rev) * 100
    elif current_rev > 0:
        pct_change = 100.0  # Prior week was $0, this week has revenue

    # Top products
    top_products = _amz_top_products(current, n=3)

    # ── Analysis signals ──

    # Revenue trend
    if pct_change is not None and pct_change < -20:
        actions.append({
            "platform": "Amazon",
            "text": f"Revenue down {abs(pct_change):.0f}% vs prior week (${current_rev:,.0f} vs ${prior_rev:,.0f}). Review BSR and pricing in Seller Central.",
        })
    elif pct_change is not None and pct_change > 0:
        infos.append({
            "platform": "Amazon",
            "text": f"Revenue up {pct_change:.0f}% vs prior week (${current_rev:,.0f} vs ${prior_rev:,.0f}).",
        })

    # Low order velocity
    if non_pending_count < 5:
        actions.append({
            "platform": "Amazon",
            "text": f"Only {non_pending_count} completed orders this week. Review advertising spend and campaign health in Seller Central.",
        })

    # Pending spike
    if order_count > 0 and pending_count / order_count > 0.80:
        urgents.append({
            "platform": "Amazon",
            "text": f"{pending_count}/{order_count} orders still Pending ({pending_count/order_count:.0%}). Possible payment or fulfillment issue — check Seller Central.",
        })

    # General info: week summary
    if order_count == 0:
        urgents.append({
            "platform": "Amazon",
            "text": "Zero orders this week on Amazon. Verify account health and listing status.",
        })
    else:
        infos.append({
            "platform": "Amazon",
            "text": f"Week summary: {order_count} orders, ${current_rev:,.0f} revenue, ${aov:,.0f} AOV.",
        })

    return {
        "error": None,
        "revenue": current_rev,
        "orders": order_count,
        "pending_count": pending_count,
        "aov": aov,
        "prior_revenue": prior_rev,
        "pct_change": pct_change,
        "top_products": top_products,
        "urgents": urgents,
        "actions": actions,
        "infos": infos,
    }


# ── Walmart Marketplace API ───────────────────────────────────────────────────

def _wm_get_token(env_vars: dict) -> str:
    """Authenticate with Walmart Marketplace and return an access token."""
    creds = base64.b64encode(
        f"{env_vars['WALMART_CLIENT_ID']}:{env_vars['WALMART_CLIENT_SECRET']}".encode()
    ).decode()

    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(
        "https://marketplace.walmartapis.com/v3/token",
        data=body,
        method="POST",
    )
    req.add_header("Authorization", f"Basic {creds}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/json")
    req.add_header("WM_SVC.NAME", "Nature's Seed")
    req.add_header("WM_QOS.CORRELATION_ID", str(uuid.uuid4()))

    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())["access_token"]


def _wm_request(token: str, url: str, params: dict = None):
    """
    Make an authenticated GET request to the Walmart Marketplace API.
    Returns parsed JSON dict, or None on 404 (no data — not an error).
    """
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url)
    req.add_header("WM_SEC.ACCESS_TOKEN", token)
    req.add_header("WM_SVC.NAME", "Nature's Seed")
    req.add_header("WM_QOS.CORRELATION_ID", str(uuid.uuid4()))
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # No orders / no data — not an error
        body = e.read().decode()
        log.error(f"Walmart API error {e.code}: {body[:300]}")
        raise


def pull_walmart_data(env_vars: dict) -> dict:
    """
    Pull last 7 days of Walmart orders and item status.
    Returns dict with 'orders', 'item_count', 'unpublished_items', 'error'.
    """
    try:
        token = _wm_get_token(env_vars)
    except Exception as e:
        return {"error": f"Auth failed: {e}", "orders": [], "item_count": 0, "unpublished_items": []}

    today = date.today()
    seven_ago = today - timedelta(days=7)

    # Format dates for Walmart API (ISO-8601 date strings)
    created_start = seven_ago.strftime("%Y-%m-%dT00:00:00.000Z")
    created_end = today.strftime("%Y-%m-%dT23:59:59.000Z")

    # Pull orders
    orders = []
    try:
        data = _wm_request(token, "https://marketplace.walmartapis.com/v3/orders", {
            "createdStartDate": created_start,
            "createdEndDate": created_end,
            "limit": 200,
        })
        if data:
            elements = (
                data.get("list", {})
                    .get("elements", {})
                    .get("order", [])
            )
            if isinstance(elements, dict):
                elements = [elements]  # Single order returned as dict
            orders = elements
    except Exception as e:
        return {"error": f"Orders fetch failed: {e}", "orders": [], "item_count": 0, "unpublished_items": []}

    # Item count
    item_count = 0
    try:
        item_data = _wm_request(token, "https://marketplace.walmartapis.com/v3/items", {"limit": 1})
        if item_data:
            item_count = item_data.get("totalItems", 0)
    except Exception as e:
        log.warning(f"Could not fetch Walmart item count: {e}")

    # Unpublished items
    unpublished_items = []
    try:
        unpub_data = _wm_request(token, "https://marketplace.walmartapis.com/v3/items", {
            "publishedStatus": "UNPUBLISHED",
            "limit": 20,
        })
        if unpub_data:
            items_list = unpub_data.get("ItemResponse", [])
            if isinstance(items_list, dict):
                items_list = [items_list]
            unpublished_items = items_list
    except Exception as e:
        log.warning(f"Could not fetch Walmart unpublished items: {e}")

    return {
        "error": None,
        "orders": orders,
        "item_count": item_count,
        "unpublished_items": unpublished_items,
        "date_range": f"{created_start} → {created_end}",
    }


def _wm_order_revenue(order: dict) -> float:
    """Sum PRODUCT charges across all line items in a Walmart order."""
    total = 0.0
    line_items = order.get("orderLines", {}).get("orderLine", [])
    if isinstance(line_items, dict):
        line_items = [line_items]
    for line in line_items:
        charges = line.get("charges", {}).get("charge", [])
        if isinstance(charges, dict):
            charges = [charges]
        for charge in charges:
            if charge.get("chargeType") == "PRODUCT":
                try:
                    total += float(charge.get("chargeAmount", {}).get("amount", 0))
                except (ValueError, TypeError):
                    pass
    return total


def _wm_top_products(orders: list, n: int = 3) -> list:
    """Identify top N Walmart products by revenue this week."""
    product_rev = {}
    product_cnt = {}

    for order in orders:
        line_items = order.get("orderLines", {}).get("orderLine", [])
        if isinstance(line_items, dict):
            line_items = [line_items]

        for line in line_items:
            item = line.get("item", {})
            name = item.get("productName", "Unknown Product")[:60]
            charges = line.get("charges", {}).get("charge", [])
            if isinstance(charges, dict):
                charges = [charges]
            rev = 0.0
            for charge in charges:
                if charge.get("chargeType") == "PRODUCT":
                    try:
                        rev += float(charge.get("chargeAmount", {}).get("amount", 0))
                    except (ValueError, TypeError):
                        pass
            if rev > 0:
                product_rev[name] = product_rev.get(name, 0.0) + rev
                product_cnt[name] = product_cnt.get(name, 0) + 1

    results = [
        {"name": name, "revenue": rev, "orders": product_cnt.get(name, 0)}
        for name, rev in sorted(product_rev.items(), key=lambda x: -x[1])
    ]
    return results[:n]


def analyze_walmart(data: dict) -> dict:
    """
    Analyze Walmart pull data and return structured findings.
    Returns: {revenue, orders, aov, item_count, unpublished_count,
              top_products, urgents, actions, infos}
    """
    urgents = []
    actions = []
    infos = []

    if data.get("error"):
        return {
            "error": data["error"],
            "revenue": 0,
            "orders": 0,
            "aov": 0,
            "item_count": 0,
            "unpublished_count": 0,
            "top_products": [],
            "urgents": [],
            "actions": [{"platform": "Walmart", "text": f"Could not pull Walmart data: {data['error']}"}],
            "infos": [],
        }

    orders = data.get("orders", [])
    unpublished = data.get("unpublished_items", [])
    item_count = data.get("item_count", 0)

    revenue = sum(_wm_order_revenue(o) for o in orders)
    order_count = len(orders)
    aov = (revenue / order_count) if order_count > 0 else 0.0

    top_products = _wm_top_products(orders, n=3)

    # ── Analysis signals ──

    # Unpublished items — urgent
    if unpublished:
        names = [
            i.get("itemResponse", {}).get("productName") or
            i.get("sku", "Unknown SKU")
            for i in unpublished[:5]
        ]
        urgents.append({
            "platform": "Walmart",
            "text": f"{len(unpublished)} item(s) UNPUBLISHED on Walmart. Fix in Seller Center: {', '.join(str(n) for n in names)}",
        })

    # Low revenue week
    if revenue < 500:
        actions.append({
            "platform": "Walmart",
            "text": f"Walmart revenue this week: ${revenue:,.0f} (below $500 threshold). Review pricing and item content.",
        })

    # Zero orders
    if order_count == 0:
        urgents.append({
            "platform": "Walmart",
            "text": "Zero Walmart orders this week. Verify item status, pricing, and Buy Box eligibility.",
        })

    # Top item high velocity — ensure inventory
    if top_products and top_products[0]["orders"] >= 5:
        top = top_products[0]
        actions.append({
            "platform": "Walmart",
            "text": f"High velocity on '{top['name']}' ({top['orders']} orders, ${top['revenue']:,.0f}). Verify inventory is adequate to avoid stockout.",
        })

    # General info
    if order_count > 0:
        infos.append({
            "platform": "Walmart",
            "text": f"Week summary: {order_count} orders, ${revenue:,.0f} revenue, ${aov:,.0f} AOV. Active items: {item_count}.",
        })

    return {
        "error": None,
        "revenue": revenue,
        "orders": order_count,
        "aov": aov,
        "item_count": item_count,
        "unpublished_count": len(unpublished),
        "top_products": top_products,
        "urgents": urgents,
        "actions": actions,
        "infos": infos,
    }


# ── Message Formatting ────────────────────────────────────────────────────────

def format_message(
    amz_data: dict,
    amz_analysis: dict,
    wm_data: dict,
    wm_analysis: dict,
    action_items: list,
) -> str:
    """Build the full Telegram report message in HTML format."""
    day_name = datetime.now().strftime("%A")
    report_date = date.today().strftime("%B %d, %Y")

    lines = [
        f"🛒 <b>Marketplace Review — {day_name}, {report_date}</b>",
        "<i>Tue/Fri optimization review</i>",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "📦 <b>AMAZON — Last 7 Days</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if amz_analysis.get("error"):
        lines.append(f"⚠️ [Amazon] Could not pull data: {amz_analysis['error']}")
    else:
        rev = amz_analysis["revenue"]
        ord_cnt = amz_analysis["orders"]
        aov = amz_analysis["aov"]
        pct = amz_analysis.get("pct_change")

        pct_str = ""
        if pct is not None:
            direction = "+" if pct >= 0 else ""
            pct_str = f" | vs Prior Week: <b>{direction}{pct:.0f}%</b>"

        lines.append(
            f"Revenue: <b>${rev:,.0f}</b> | Orders: <b>{ord_cnt}</b> | AOV: <b>${aov:,.0f}</b>{pct_str}"
        )

        if amz_analysis.get("pending_count", 0) > 0:
            lines.append(f"⏳ Pending: {amz_analysis['pending_count']} orders (not counted in revenue)")

        top = amz_analysis.get("top_products", [])
        if top:
            lines.append("")
            lines.append("🏆 <b>Top Products:</b>")
            for i, p in enumerate(top, 1):
                lines.append(f"  {i}. {p['name']} — ${p['revenue']:,.0f} ({p['orders']} orders)")

        for item in amz_analysis.get("urgents", []):
            lines.append(f"\n🔴 <b>URGENT:</b> {item['text']}")
        for item in amz_analysis.get("actions", []):
            lines.append(f"\n🟡 <b>ACTION:</b> {item['text']}")
        for item in amz_analysis.get("infos", []):
            lines.append(f"\n🔵 <b>INFO:</b> {item['text']}")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "🏪 <b>WALMART — Last 7 Days</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if wm_analysis.get("error"):
        lines.append(f"⚠️ [Walmart] Could not pull data: {wm_analysis['error']}")
    else:
        rev = wm_analysis["revenue"]
        ord_cnt = wm_analysis["orders"]
        aov = wm_analysis["aov"]
        item_count = wm_analysis["item_count"]

        lines.append(
            f"Revenue: <b>${rev:,.0f}</b> | Orders: <b>{ord_cnt}</b> | AOV: <b>${aov:,.0f}</b>"
        )
        lines.append(f"Active Items: <b>{item_count}</b>")

        if wm_analysis.get("unpublished_count", 0) > 0:
            lines.append(f"🚨 Unpublished Items: <b>{wm_analysis['unpublished_count']}</b>")

        top = wm_analysis.get("top_products", [])
        if top:
            lines.append("")
            lines.append("🏆 <b>Top Products:</b>")
            for i, p in enumerate(top, 1):
                lines.append(f"  {i}. {p['name']} — ${p['revenue']:,.0f} ({p['orders']} orders)")

        for item in wm_analysis.get("urgents", []):
            lines.append(f"\n🔴 <b>URGENT:</b> {item['text']}")
        for item in wm_analysis.get("actions", []):
            lines.append(f"\n🟡 <b>ACTION:</b> {item['text']}")
        for item in wm_analysis.get("infos", []):
            lines.append(f"\n🔵 <b>INFO:</b> {item['text']}")

    # Action items requiring approval
    if action_items:
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "📋 <b>ACTION ITEMS REQUIRING APPROVAL</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
        ]
        for i, item in enumerate(action_items, 1):
            platform = item.get("platform", "?")
            lines.append(f"<b>{i}.</b> [{platform}] {item['text']}")

        lines += [
            "",
            "Reply with action numbers to approve (e.g. <code>1 3</code>), <code>all</code> to approve all, or <code>skip</code> to skip.",
        ]

    return "\n".join(lines)


# ── Approval Flow ─────────────────────────────────────────────────────────────

def run_approval_flow(token: str, chat_id: str, action_items: list) -> list:
    """
    Wait for user to reply with action numbers, 'all', or 'skip'.
    Returns list of approved action dicts.
    """
    reply = poll_telegram(token, chat_id, timeout_seconds=APPROVAL_TIMEOUT)

    if not reply:
        log.info("No reply received — skipping all actions")
        return []

    reply_lower = reply.strip().lower()

    if reply_lower == "skip":
        log.info("User replied 'skip' — skipping all actions")
        return []

    if reply_lower == "all":
        log.info("User approved all actions")
        return action_items

    # Parse space-separated or comma-separated numbers
    approved = []
    import re
    numbers = re.findall(r"\d+", reply)
    approved_indices = set()
    for n in numbers:
        idx = int(n)
        if 1 <= idx <= len(action_items):
            approved_indices.add(idx)

    for i, item in enumerate(action_items, 1):
        if i in approved_indices:
            approved.append(item)

    log.info(f"User approved {len(approved)}/{len(action_items)} actions: {sorted(approved_indices)}")
    return approved


# ── Action Log ────────────────────────────────────────────────────────────────

def _ensure_action_log() -> None:
    """Create action_log.md with a header if it doesn't exist."""
    if not ACTION_LOG_PATH.exists():
        ACTION_LOG_PATH.write_text(
            "# Marketplace Action Log\n\n"
            "Approved actions from the Tue/Fri marketplace review bot.\n"
            "These require manual execution in Seller Central or Walmart Seller Center.\n\n"
            "---\n\n"
        )
        log.info(f"Created {ACTION_LOG_PATH}")


def log_actions(
    approved: list,
    all_items: list,
    amz_analysis: dict,
    wm_analysis: dict,
) -> None:
    """
    Append this run's approved/skipped actions to action_log.md.
    """
    _ensure_action_log()

    today_str = date.today().isoformat()
    day_name = datetime.now().strftime("%A")

    amz_approved = [a for a in approved if a.get("platform") == "Amazon"]
    wm_approved = [a for a in approved if a.get("platform") == "Walmart"]
    amz_skipped = [a for a in all_items if a not in approved and a.get("platform") == "Amazon"]
    wm_skipped = [a for a in all_items if a not in approved and a.get("platform") == "Walmart"]

    entry_lines = [
        f"## {today_str} ({day_name} Review)\n",
    ]

    if amz_approved or amz_skipped:
        entry_lines.append("### Amazon Actions")
        for item in amz_approved:
            entry_lines.append(f"- [APPROVED] {item['text']}")
        for item in amz_skipped:
            entry_lines.append(f"- [SKIPPED] {item['text']}")
        entry_lines.append("")

    if wm_approved or wm_skipped:
        entry_lines.append("### Walmart Actions")
        for item in wm_approved:
            entry_lines.append(f"- [APPROVED] {item['text']}")
        for item in wm_skipped:
            entry_lines.append(f"- [SKIPPED] {item['text']}")
        entry_lines.append("")

    entry_lines.append("---\n")

    with open(ACTION_LOG_PATH, "a") as f:
        f.write("\n".join(entry_lines))

    log.info(f"Action log updated: {len(approved)} approved, {len(all_items) - len(approved)} skipped")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Marketplace Bot ===")
    print(f"Run date: {date.today()}, {datetime.now().strftime('%A')}")

    # Load credentials
    try:
        env_vars = _load_env()
    except FileNotFoundError as e:
        print(f"FATAL: {e}")
        return

    token = env_vars.get("TELEGRAM_BOT_TOKEN") or env_vars.get("TELEGRAM_BOT_API")
    chat_id = env_vars.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("FATAL: TELEGRAM_BOT_TOKEN/TELEGRAM_BOT_API and TELEGRAM_CHAT_ID must be set in .env")
        return

    # ── 1. Pull data ──
    print("\n[1/4] Pulling Amazon data...")
    try:
        amz_data = pull_amazon_data(env_vars)
        if amz_data.get("error"):
            print(f"  Amazon error: {amz_data['error']}")
        else:
            print(f"  Amazon: {len(amz_data.get('current_orders', []))} orders this week")
    except Exception as e:
        log.error(f"Unexpected Amazon pull error: {e}")
        amz_data = {"error": str(e), "current_orders": [], "prior_orders": []}

    print("[1/4] Pulling Walmart data...")
    try:
        wm_data = pull_walmart_data(env_vars)
        if wm_data.get("error"):
            print(f"  Walmart error: {wm_data['error']}")
        else:
            print(f"  Walmart: {len(wm_data.get('orders', []))} orders this week")
    except Exception as e:
        log.error(f"Unexpected Walmart pull error: {e}")
        wm_data = {"error": str(e), "orders": [], "item_count": 0, "unpublished_items": []}

    # ── 2. Analyze ──
    print("\n[2/4] Analyzing data...")
    amz_analysis = analyze_amazon(amz_data)
    wm_analysis = analyze_walmart(wm_data)

    all_action_items = amz_analysis.get("actions", []) + wm_analysis.get("actions", [])
    all_urgent_items = amz_analysis.get("urgents", []) + wm_analysis.get("urgents", [])

    print(f"  Amazon: {len(amz_analysis.get('urgents', []))} urgent, {len(amz_analysis.get('actions', []))} action, {len(amz_analysis.get('infos', []))} info")
    print(f"  Walmart: {len(wm_analysis.get('urgents', []))} urgent, {len(wm_analysis.get('actions', []))} action, {len(wm_analysis.get('infos', []))} info")

    # ── 3. Build and send message ──
    print("\n[3/4] Sending Telegram report...")
    message = format_message(amz_data, amz_analysis, wm_data, wm_analysis, all_action_items)

    try:
        send_telegram(token, chat_id, message)
        print("  Report sent.")
    except Exception as e:
        print(f"  WARN: Telegram send failed: {e}")
        print("  Report would have been:")
        print(message[:500])

    # ── 4. Approval flow ──
    if all_action_items:
        print(f"\n[4/4] Waiting for approval of {len(all_action_items)} action item(s)...")
        try:
            approved = run_approval_flow(token, chat_id, all_action_items)
        except Exception as e:
            log.error(f"Approval flow error: {e}")
            approved = []

        _ensure_action_log()
        log_actions(approved, all_action_items, amz_analysis, wm_analysis)

        if approved:
            confirmation = (
                f"✅ <b>{len(approved)} action(s) logged</b> to <code>action_log.md</code>.\n"
                f"Check the log for your to-do list before your next Seller Central session."
            )
        else:
            confirmation = "⏭️ All actions skipped. No items logged."

        try:
            send_telegram(token, chat_id, confirmation)
        except Exception as e:
            print(f"  WARN: Could not send confirmation: {e}")
            print(f"  Confirmation: {confirmation}")
    else:
        print("\n[4/4] No action items this week.")
        try:
            send_telegram(token, chat_id, "✅ No action items this week. Marketplaces looking good!")
        except Exception as e:
            print(f"  WARN: Could not send no-action message: {e}")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
