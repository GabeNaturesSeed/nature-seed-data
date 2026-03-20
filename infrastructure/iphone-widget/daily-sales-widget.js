// Nature's Seed — Daily Sales Widget for Scriptable (iOS)
// Shows today's WooCommerce revenue + order count, refreshes every 15 min
//
// SETUP:
// 1. Install "Scriptable" from the App Store
// 2. Create a new script, paste this entire file
// 3. Replace WC_CK and WC_CS below with your real keys from .env
// 4. Add a Scriptable widget to your home screen, select this script
//
// Your phone's residential IP bypasses Cloudflare Bot Fight Mode —
// no proxy needed.

// ── Config ──────────────────────────────────────────────────────────
const WC_CK = "YOUR_CONSUMER_KEY";
const WC_CS = "YOUR_CONSUMER_SECRET";
const WC_BASE = "https://naturesseed.com/wp-json/wc/v3";
// ────────────────────────────────────────────────────────────────────

/**
 * Fetch today's WooCommerce orders for a given status.
 * Paginates automatically (100 per page).
 */
async function fetchOrders(status) {
  const now = new Date();
  // Today midnight in local time (MST/MDT)
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const after = startOfDay.toISOString();
  const before = now.toISOString();

  const auth = btoa(`${WC_CK}:${WC_CS}`);
  let allOrders = [];
  let page = 1;

  while (true) {
    const url = `${WC_BASE}/orders?status=${status}&after=${after}&before=${before}&per_page=100&page=${page}`;
    const req = new Request(url);
    req.headers = {
      "Authorization": `Basic ${auth}`,
      "User-Agent": "NaturesSeed-iPhoneWidget/1.0",
    };
    req.timeoutInterval = 30;

    try {
      const orders = await req.loadJSON();
      if (!Array.isArray(orders) || orders.length === 0) break;
      allOrders = allOrders.concat(orders);
      if (orders.length < 100) break;
      page++;
    } catch (e) {
      console.error(`Error fetching ${status} orders page ${page}: ${e}`);
      break;
    }
  }
  return allOrders;
}

/**
 * Pull today's completed + processing orders, return summary.
 */
async function getTodaySales() {
  const [completed, processing] = await Promise.all([
    fetchOrders("completed"),
    fetchOrders("processing"),
  ]);

  const allOrders = completed.concat(processing);

  const revenue = allOrders.reduce((sum, o) => sum + parseFloat(o.total || 0), 0);
  const orderCount = allOrders.length;
  const units = allOrders.reduce((sum, o) => {
    return sum + (o.line_items || []).reduce((s, item) => s + (item.quantity || 0), 0);
  }, 0);

  return { revenue, orderCount, units };
}

// ── Widget rendering ────────────────────────────────────────────────

function formatCurrency(n) {
  return "$" + n.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function formatTime(d) {
  let h = d.getHours();
  const m = String(d.getMinutes()).padStart(2, "0");
  const ampm = h >= 12 ? "PM" : "AM";
  h = h % 12 || 12;
  return `${h}:${m} ${ampm}`;
}

async function createWidget(sales) {
  const w = new ListWidget();

  // Background — dark green gradient
  const g = new LinearGradient();
  g.locations = [0, 1];
  g.colors = [new Color("#0f2419"), new Color("#1a3a2a")];
  w.backgroundGradient = g;

  w.setPadding(16, 16, 16, 16);

  // Title row
  const titleStack = w.addStack();
  titleStack.layoutHorizontally();
  titleStack.centerAlignContent();

  const icon = titleStack.addText("🌱");
  icon.font = Font.systemFont(13);

  titleStack.addSpacer(4);

  const title = titleStack.addText("Nature's Seed");
  title.font = Font.semiboldSystemFont(13);
  title.textColor = new Color("#86efac");

  w.addSpacer(6);

  // Revenue — big number
  const revText = w.addText(formatCurrency(sales.revenue));
  revText.font = Font.boldSystemFont(32);
  revText.textColor = Color.white();
  revText.minimumScaleFactor = 0.6;

  w.addSpacer(4);

  // Orders + units
  const detailText = w.addText(`${sales.orderCount} orders · ${sales.units} units`);
  detailText.font = Font.mediumSystemFont(12);
  detailText.textColor = new Color("#a7f3d0");

  w.addSpacer(null);

  // Last updated timestamp
  const updatedText = w.addText(`Updated ${formatTime(new Date())}`);
  updatedText.font = Font.systemFont(10);
  updatedText.textColor = new Color("#6b7280");

  // Refresh every 15 minutes
  const nextRefresh = new Date(Date.now() + 15 * 60 * 1000);
  w.refreshAfterDate = nextRefresh;

  return w;
}

async function createErrorWidget(message) {
  const w = new ListWidget();
  w.backgroundColor = new Color("#1a1a2e");
  w.setPadding(16, 16, 16, 16);

  const title = w.addText("Nature's Seed");
  title.font = Font.boldSystemFont(14);
  title.textColor = new Color("#f87171");

  w.addSpacer(8);

  const err = w.addText(message);
  err.font = Font.systemFont(11);
  err.textColor = Color.white();

  const nextRefresh = new Date(Date.now() + 15 * 60 * 1000);
  w.refreshAfterDate = nextRefresh;

  return w;
}

// ── Main ────────────────────────────────────────────────────────────

try {
  const sales = await getTodaySales();
  const widget = await createWidget(sales);

  if (config.runsInWidget) {
    Script.setWidget(widget);
  } else {
    // Preview when running in-app
    await widget.presentSmall();
  }
} catch (e) {
  console.error(`Widget error: ${e}`);
  const widget = await createErrorWidget("API error — check keys");
  if (config.runsInWidget) {
    Script.setWidget(widget);
  } else {
    await widget.presentSmall();
  }
}

Script.complete();
