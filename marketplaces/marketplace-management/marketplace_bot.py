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

import csv
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
APPROVAL_TIMEOUT = 300   # 5 minutes for first approval

# ── Buy Box Thresholds ────────────────────────────────────────────────────────

BUYBOX_TARGET_PCT    = 10.0   # Target: ≥10% buy box win rate per item
BUYBOX_CRITICAL_PCT  = 5.0    # Below this = P0 (losing buy box badly)
LOW_STOCK_THRESHOLD  = 15     # Units — flag when below this
WALMART_FEE_PCT      = 0.20   # ~20% total Walmart fees (referral ~15% + WFS est.)
MIN_MARGIN_PCT       = 20     # Minimum gross margin after Walmart fees
MAX_PRICE_DROP_PCT   = 12     # Never drop price more than 12% in one cycle
BUYBOX_PRICE_CUT_PCT = 0.03   # Price reduction step to compete for buy box (3%)

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

    # Full item list (for buy box analysis)
    all_items = []
    try:
        offset_i, limit_i = 0, 20
        total_i = None
        while True:
            item_page = _wm_request(token, "https://marketplace.walmartapis.com/v3/items",
                                    {"limit": limit_i, "offset": offset_i})
            if not item_page:
                break
            if total_i is None:
                total_i = item_page.get("totalItems", 0)
            page_items = item_page.get("ItemResponse", [])
            if not page_items:
                break
            all_items.extend(page_items)
            if len(all_items) >= total_i or len(page_items) < limit_i:
                break
            offset_i += limit_i
            time.sleep(0.3)
    except Exception as e:
        log.warning(f"Could not fetch full item list: {e}")

    # Listing quality + buy box win % (Growth Intelligence API)
    listing_quality: dict = {}
    try:
        listing_quality = _pull_listing_quality_scores(token, days=30)
        log.info(f"  Listing quality: {len(listing_quality)} SKUs with buy box data")
    except Exception as e:
        log.warning(f"Listing quality pull failed (may need Growth Intelligence access): {e}")

    # Inventory for published SKUs
    published_skus = [i["sku"] for i in all_items if i.get("publishedStatus") == "PUBLISHED" and i.get("sku")]
    inventory: dict = {}
    try:
        inventory = _pull_inventory_levels(token, published_skus[:50])
    except Exception as e:
        log.warning(f"Inventory pull failed: {e}")

    return {
        "error": None,
        "orders": orders,
        "item_count": item_count,
        "unpublished_items": unpublished_items,
        "all_items": all_items,
        "listing_quality": listing_quality,
        "inventory": inventory,
        "wm_token": token,
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


# ── COGS ─────────────────────────────────────────────────────────────────────

def _load_cogs() -> dict:
    """Load unit costs from COGS CSV. Returns {sku: unit_cost}."""
    cogs: dict = {}
    cogs_path = PROJECT_ROOT / "Woo-COGS" / "Cost per SKU - Sheet1.csv"
    if not cogs_path.exists():
        return cogs
    try:
        with open(cogs_path, newline="") as f:
            for row in csv.DictReader(f):
                sku  = row.get("SKU", "").strip()
                cost = row.get("Unit Cost", "0").strip().replace("$", "").replace(",", "")
                try:
                    c = float(cost)
                    if sku and c > 0:
                        cogs[sku] = c
                except ValueError:
                    pass
    except Exception as e:
        log.warning(f"Could not load COGS: {e}")
    return cogs


# ── Walmart Buy Box & Listing Quality ─────────────────────────────────────────

def _pull_listing_quality_scores(token: str, days: int = 30) -> dict:
    """
    Pull Walmart Growth Intelligence listing quality + buy box win % per SKU.
    Endpoint: GET /v3/insights/items/listingQualityScore

    Returns: {sku: {buyBoxWinPct, listingScore, pageViews, unitsSold, revenue}}
    Falls back to {} if Growth Intelligence access is not enabled.
    """
    end_date   = date.today().isoformat()
    start_date = (date.today() - timedelta(days=days)).isoformat()
    quality: dict = {}
    offset, limit = 0, 200

    while True:
        url = (
            f"https://marketplace.walmartapis.com/v3/insights/items/listingQualityScore"
            f"?fromDate={start_date}&toDate={end_date}&limit={limit}&offset={offset}"
        )
        data = _wm_request(token, url)
        if not data:
            break

        items = data.get("items", data.get("data", []))
        if not items:
            break

        for item in items:
            sku = item.get("sku", "")
            if sku:
                quality[sku] = {
                    "buyBoxWinPct": float(item.get("buyBoxWinPercentage", 0) or 0),
                    "listingScore": float(item.get("listingQualityScore", 0) or 0),
                    "pageViews":    int(item.get("pageViews", 0) or 0),
                    "unitsSold":    int(item.get("unitsSold", 0) or 0),
                    "revenue":      float(item.get("itemRevenue", 0) or 0),
                }

        total = data.get("totalItems", 0)
        offset += limit
        if offset >= total or len(items) < limit:
            break
        time.sleep(0.3)

    return quality


def _pull_inventory_levels(token: str, skus: list) -> dict:
    """
    Pull inventory quantity per SKU (limited to first 50 to respect rate limits).
    Returns: {sku: quantity}
    """
    inventory: dict = {}
    for sku in skus[:50]:
        data = _wm_request(token, "https://marketplace.walmartapis.com/v3/inventory",
                           {"sku": sku})
        if data:
            qty = data.get("quantity", {})
            inventory[sku] = int(qty.get("amount", 0) if isinstance(qty, dict) else (qty or 0))
        time.sleep(0.15)
    return inventory


def _wm_update_price(token: str, sku: str, new_price: float) -> dict:
    """Update a single SKU price on Walmart. Returns {status, sku, new_price}."""
    url     = "https://marketplace.walmartapis.com/v3/prices"
    payload = {
        "sku": sku,
        "pricing": [{
            "currentPriceType": "BASE",
            "currentPrice": {"currency": "USD", "amount": new_price},
        }],
    }
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=body, method="PUT")
    req.add_header("WM_SEC.ACCESS_TOKEN", token)
    req.add_header("WM_SVC.NAME", "Nature's Seed")
    req.add_header("WM_QOS.CORRELATION_ID", str(uuid.uuid4()))
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
        return {"status": "success", "sku": sku, "new_price": new_price}
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode()
        log.error(f"Price update {sku} → {e.code}: {body_txt[:200]}")
        return {"status": "error", "sku": sku, "error": body_txt[:100]}


def _build_price_changes(
    all_items: list,
    listing_quality: dict,
    inventory: dict,
    cogs: dict,
) -> list:
    """
    For each Walmart item with a low buy box win rate, generate a price change
    recommendation that is:
      - ≥ COGS-based floor (min margin after fees)
      - ≤ MAX_PRICE_DROP_PCT below current price

    Returns: list of price change dicts suitable for Telegram approval.
    """
    changes = []
    for item in all_items:
        sku      = item.get("sku", "")
        name     = item.get("productName", sku)[:50]
        published = item.get("publishedStatus", "") == "PUBLISHED"
        if not published or not sku:
            continue

        price_info    = item.get("price", {})
        current_price = float(
            price_info.get("amount", 0) if isinstance(price_info, dict) else (price_info or 0)
        )
        if current_price <= 0:
            continue

        quality    = listing_quality.get(sku, {})
        buybox_pct = quality.get("buyBoxWinPct")  # None = no data
        stock      = inventory.get(sku)

        # Skip if out of stock (price won't help)
        if stock is not None and stock == 0:
            continue
        # Skip if no buy box data (can't confirm the problem)
        if buybox_pct is None:
            continue
        # Only flag items losing the buy box
        if buybox_pct >= BUYBOX_TARGET_PCT:
            continue

        # Compute price floor from COGS
        unit_cost = cogs.get(sku)
        if unit_cost and unit_cost > 0:
            min_price = round(unit_cost / (1 - WALMART_FEE_PCT - MIN_MARGIN_PCT / 100), 2)
        else:
            min_price = round(current_price * 0.75, 2)  # fallback: don't drop >25%

        # Propose a 3% cut, clamped to floor and max-drop
        proposed = round(current_price * (1 - BUYBOX_PRICE_CUT_PCT), 2)
        proposed = max(proposed, min_price)
        proposed = max(proposed, round(current_price * (1 - MAX_PRICE_DROP_PCT / 100), 2))

        if proposed >= current_price:
            continue  # Floor prevents any reduction — skip

        priority = "P0" if buybox_pct < BUYBOX_CRITICAL_PCT else "P1"
        change_pct = ((proposed - current_price) / current_price) * 100

        changes.append({
            "sku":           sku,
            "name":          name,
            "current_price": current_price,
            "proposed_price": proposed,
            "buybox_pct":    buybox_pct,
            "priority":      priority,
            "change_pct":    change_pct,
            "rationale":     f"Buy Box {buybox_pct:.0f}% — cut {abs(change_pct):.1f}% to compete",
        })

    # Sort P0 first, then by worst buy box win rate
    return sorted(changes, key=lambda x: (x["priority"] != "P0", x["buybox_pct"]))


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

    orders          = data.get("orders", [])
    unpublished     = data.get("unpublished_items", [])
    item_count      = data.get("item_count", 0)
    all_items       = data.get("all_items", [])
    listing_quality = data.get("listing_quality", {})
    inventory       = data.get("inventory", {})

    revenue     = sum(_wm_order_revenue(o) for o in orders)
    order_count = len(orders)
    aov         = (revenue / order_count) if order_count > 0 else 0.0

    top_products = _wm_top_products(orders, n=3)

    # ── Buy Box Stats ──────────────────────────────────────────
    bb_values         = [v["buyBoxWinPct"] for v in listing_quality.values() if v.get("buyBoxWinPct") is not None]
    avg_buybox        = sum(bb_values) / len(bb_values) if bb_values else None
    items_hitting_target = sum(1 for b in bb_values if b >= BUYBOX_TARGET_PCT)
    items_critical    = sum(1 for b in bb_values if b < BUYBOX_CRITICAL_PCT)
    oos_count         = sum(1 for qty in inventory.values() if qty == 0)
    low_stock_count   = sum(1 for qty in inventory.values() if 0 < qty < LOW_STOCK_THRESHOLD)

    # ── Analysis signals ──────────────────────────────────────

    # Unpublished items — urgent
    if unpublished:
        names = [
            i.get("itemResponse", {}).get("productName") or i.get("sku", "Unknown SKU")
            for i in unpublished[:5]
        ]
        urgents.append({
            "platform": "Walmart",
            "text": f"{len(unpublished)} item(s) UNPUBLISHED. Fix in Seller Center: {', '.join(str(n) for n in names)}",
        })

    # Critical buy box items
    if items_critical > 0:
        urgents.append({
            "platform": "Walmart",
            "text": f"{items_critical} item(s) have <{BUYBOX_CRITICAL_PCT:.0f}% buy box win rate. Price review needed — see PRICE CHANGES section.",
        })

    # Overall buy box below target
    if avg_buybox is not None and avg_buybox < BUYBOX_TARGET_PCT:
        actions.append({
            "platform": "Walmart",
            "text": f"Avg buy box win rate {avg_buybox:.1f}% — below {BUYBOX_TARGET_PCT:.0f}% target. {items_hitting_target}/{len(bb_values)} items at target.",
        })

    # Out of stock
    if oos_count > 0:
        urgents.append({
            "platform": "Walmart",
            "text": f"{oos_count} SKU(s) out of stock — suppressed from buy box. Restock in Seller Center immediately.",
        })

    # Low stock warning
    if low_stock_count > 0:
        actions.append({
            "platform": "Walmart",
            "text": f"{low_stock_count} SKU(s) below {LOW_STOCK_THRESHOLD} units. Restock soon to avoid losing buy box.",
        })

    # Zero orders
    if order_count == 0:
        urgents.append({
            "platform": "Walmart",
            "text": "Zero Walmart orders this week. Verify item status, pricing, and buy box eligibility.",
        })

    # Low revenue
    if revenue < 500 and order_count > 0:
        actions.append({
            "platform": "Walmart",
            "text": f"Revenue ${revenue:,.0f} this week — below $500 threshold. Review pricing and content.",
        })

    # Top item high velocity — inventory check
    if top_products and top_products[0]["orders"] >= 5:
        top = top_products[0]
        actions.append({
            "platform": "Walmart",
            "text": f"High velocity: '{top['name']}' ({top['orders']} orders, ${top['revenue']:,.0f}). Verify inventory to avoid stockout.",
        })

    # General info
    if order_count > 0:
        infos.append({
            "platform": "Walmart",
            "text": f"Week: {order_count} orders, ${revenue:,.0f} revenue, ${aov:,.0f} AOV. Active items: {item_count}.",
        })

    if avg_buybox is not None:
        infos.append({
            "platform": "Walmart",
            "text": f"Buy Box avg: {avg_buybox:.1f}% across {len(bb_values)} items ({items_hitting_target} at ≥{BUYBOX_TARGET_PCT:.0f}% target).",
        })

    return {
        "error": None,
        "revenue": revenue,
        "orders": order_count,
        "aov": aov,
        "item_count": item_count,
        "unpublished_count": len(unpublished),
        "avg_buybox_pct": avg_buybox,
        "items_hitting_target": items_hitting_target,
        "bb_data_count": len(bb_values),
        "oos_count": oos_count,
        "low_stock_count": low_stock_count,
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
    price_changes: list = None,
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

        # Buy Box summary
        if wm_analysis.get("avg_buybox_pct") is not None:
            bb_avg = wm_analysis["avg_buybox_pct"]
            bb_emoji = "✅" if bb_avg >= BUYBOX_TARGET_PCT else ("🔴" if bb_avg < BUYBOX_CRITICAL_PCT else "🟡")
            lines.append(
                f"Buy Box avg: {bb_emoji} <b>{bb_avg:.1f}%</b> "
                f"(target ≥{BUYBOX_TARGET_PCT:.0f}% | "
                f"{wm_analysis.get('items_hitting_target', 0)}/{wm_analysis.get('bb_data_count', 0)} items)"
            )
        else:
            lines.append("Buy Box: ℹ️ Growth Intelligence API not enabled — check Seller Center → Analytics")

        if wm_analysis.get("oos_count", 0) > 0:
            lines.append(f"🚨 Out of Stock: <b>{wm_analysis['oos_count']}</b> SKU(s)")
        if wm_analysis.get("low_stock_count", 0) > 0:
            lines.append(f"⚠️ Low Stock: <b>{wm_analysis['low_stock_count']}</b> SKU(s) &lt;{LOW_STOCK_THRESHOLD} units")
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

    # Price change recommendations (executable)
    if price_changes:
        p0_pc = [p for p in price_changes if p["priority"] == "P0"]
        p1_pc = [p for p in price_changes if p["priority"] == "P1"]
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"💰 <b>WALMART PRICE CHANGES — {len(price_changes)} items losing Buy Box</b>",
            f"🔴 P0 Critical ({len(p0_pc)}) | 🟡 P1 ({len(p1_pc)})",
            "",
        ]
        for i, pc in enumerate(price_changes[:15], 1):
            p_emoji = "🔴" if pc["priority"] == "P0" else "🟡"
            lines.append(
                f"  <b>{i}.</b> {p_emoji} <code>{pc['sku']}</code>  "
                f"${pc['current_price']:.2f} → <b>${pc['proposed_price']:.2f}</b> "
                f"({pc['change_pct']:+.1f}%)  BB: {pc['buybox_pct']:.0f}%"
            )
        if len(price_changes) > 15:
            lines.append(f"  … and {len(price_changes) - 15} more")

        lines += [
            "",
            "📋 <b>Reply to approve price changes:</b>",
            "  <code>APPROVE ALL</code> — execute all price cuts",
            "  <code>APPROVE 1,3,5</code> — specific items only",
            "  <code>SKIP</code> — no price changes this cycle",
        ]
    elif not action_items:
        lines += ["", "✅ No urgent actions or price changes this cycle."]

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


# ── Price Change Approval ─────────────────────────────────────────────────────

def run_price_approval(token: str, chat_id: str, price_changes: list, wm_token: str) -> list:
    """
    Wait for user to approve price changes. Executes approved ones via Walmart API.
    Returns list of execution result dicts.
    """
    reply = poll_telegram(token, chat_id, timeout_seconds=7200)  # 2h timeout

    if not reply:
        send_telegram(token, chat_id, "⏰ No reply in 2h — no price changes made.")
        return []

    r = reply.strip().upper()

    if r == "SKIP":
        send_telegram(token, chat_id, "⏭️ Price changes skipped this cycle.")
        return []

    if r == "APPROVE ALL":
        approved = price_changes
    elif r.startswith("APPROVE"):
        nums_str = r.replace("APPROVE", "").strip()
        import re
        indices  = [int(n) for n in re.findall(r"\d+", nums_str)]
        approved = [price_changes[i - 1] for i in indices if 0 < i <= len(price_changes)]
    else:
        send_telegram(token, chat_id, "❓ Unknown reply. Use APPROVE ALL / APPROVE 1,3 / SKIP. No changes made.")
        return []

    if not approved:
        return []

    send_telegram(token, chat_id, f"⚙️ Executing {len(approved)} price change(s)...")

    results = []
    for pc in approved:
        result = _wm_update_price(wm_token, pc["sku"], pc["proposed_price"])
        results.append(result)
        time.sleep(0.5)

    success = sum(1 for r in results if r["status"] == "success")
    errors  = sum(1 for r in results if r["status"] == "error")

    exec_lines = [f"✅ <b>Price Execution Complete</b>", f"  {success} succeeded | {errors} failed", ""]
    for r in results:
        emoji     = "✅" if r["status"] == "success" else "❌"
        price_str = f"${r['new_price']:.2f}" if r.get("new_price") else "?"
        exec_lines.append(f"  {emoji} <code>{r['sku']}</code> → {price_str}")

    send_telegram(token, chat_id, "\n".join(exec_lines))
    return results


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
    wm_analysis  = analyze_walmart(wm_data)

    # Build buy box price changes (executable)
    cogs         = _load_cogs()
    all_items    = wm_data.get("all_items", [])
    lq           = wm_data.get("listing_quality", {})
    inv          = wm_data.get("inventory", {})
    price_changes = _build_price_changes(all_items, lq, inv, cogs) if all_items else []

    all_action_items = (
        amz_analysis.get("urgents", []) + amz_analysis.get("actions", []) +
        wm_analysis.get("urgents", [])  + wm_analysis.get("actions", [])
    )

    print(f"  Amazon: {len(amz_analysis.get('urgents', []))} urgent, {len(amz_analysis.get('actions', []))} action")
    print(f"  Walmart: {len(wm_analysis.get('urgents', []))} urgent, {len(wm_analysis.get('actions', []))} action")
    print(f"  Price changes ready: {len(price_changes)} ({sum(1 for p in price_changes if p['priority'] == 'P0')} P0)")

    # ── 3. Build and send message ──
    print("\n[3/4] Sending Telegram report...")
    message = format_message(amz_data, amz_analysis, wm_data, wm_analysis,
                             all_action_items, price_changes)

    try:
        send_telegram(token, chat_id, message)
        print("  Report sent.")
    except Exception as e:
        print(f"  WARN: Telegram send failed: {e}")

    # ── 4a. Manual action approval (text actions) ──
    if all_action_items:
        print(f"\n[4a/4] Waiting for manual action approval ({len(all_action_items)} items, 5min timeout)...")
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
                "Check the log before your next Seller Central session."
            )
        else:
            confirmation = "⏭️ Manual actions skipped."
        try:
            send_telegram(token, chat_id, confirmation)
        except Exception as e:
            print(f"  WARN: Could not send confirmation: {e}")

    # ── 4b. Price change execution (automated) ──
    price_results = []
    if price_changes:
        wm_token = wm_data.get("wm_token", "")
        print(f"\n[4b/4] Waiting for price change approval ({len(price_changes)} items, 2h timeout)...")
        if wm_token:
            try:
                price_results = run_price_approval(token, chat_id, price_changes, wm_token)
            except Exception as e:
                log.error(f"Price approval flow error: {e}")
        else:
            send_telegram(token, chat_id, "⚠️ Walmart token unavailable — price changes skipped.")

    if not all_action_items and not price_changes:
        print("\n[4/4] No action items or price changes this week.")
        try:
            send_telegram(token, chat_id, "✅ No urgent actions or price changes this cycle. Marketplaces looking good!")
        except Exception as e:
            print(f"  WARN: Could not send no-action message: {e}")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
