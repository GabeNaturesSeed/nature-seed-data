// Nature's Seed — Daily Sales Widget for Scriptable (iOS)
// Frosted glass design · Pulls from WooCommerce every 15 min
//
// SETUP:
// 1. Install "Scriptable" from the App Store (free)
// 2. Create a new script, paste this entire file
// 3. Replace WC_CK and WC_CS below with your real keys
// 4. Long-press home screen → add Scriptable widget → select this script
//
// Runs from your phone IP — bypasses Cloudflare Bot Fight Mode.

// ── Config ──────────────────────────────────────────────────────────
const WC_CK = "YOUR_CONSUMER_KEY";
const WC_CS = "YOUR_CONSUMER_SECRET";
const WC_BASE = "https://naturesseed.com/wp-json/wc/v3";
// ────────────────────────────────────────────────────────────────────

// ── Data fetching ───────────────────────────────────────────────────

async function fetchOrders(status) {
  const now = new Date();
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
      console.error(`Error fetching ${status} page ${page}: ${e}`);
      break;
    }
  }
  return allOrders;
}

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

// ── Helpers ─────────────────────────────────────────────────────────

function fmt(n) {
  return "$" + n.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function fmtTime(d) {
  let h = d.getHours();
  const m = String(d.getMinutes()).padStart(2, "0");
  const ampm = h >= 12 ? "PM" : "AM";
  h = h % 12 || 12;
  return `${h}:${m} ${ampm}`;
}

// ── Glass background ────────────────────────────────────────────────

function drawGlassBackground(w) {
  // Soft gradient base — translucent dark with green tint
  const g = new LinearGradient();
  g.locations = [0, 0.5, 1];
  g.colors = [
    new Color("#1a2f25", 0.85),  // deep forest, slightly transparent
    new Color("#1e3a2c", 0.78),  // mid green glass
    new Color("#162b20", 0.90),  // bottom anchors darker
  ];
  w.backgroundGradient = g;
}

// ── Stat pill (glass card) ──────────────────────────────────────────

function addStatPill(parent, value, label) {
  const pill = parent.addStack();
  pill.layoutVertically();
  pill.centerAlignContent();
  pill.backgroundColor = new Color("#ffffff", 0.08);
  pill.cornerRadius = 12;
  pill.setPadding(8, 12, 8, 12);

  const valText = pill.addText(value);
  valText.font = Font.boldRoundedSystemFont(15);
  valText.textColor = Color.white();
  valText.lineLimit = 1;

  pill.addSpacer(2);

  const lblText = pill.addText(label);
  lblText.font = Font.mediumRoundedSystemFont(10);
  lblText.textColor = new Color("#a7f3d0", 0.8);
  lblText.lineLimit = 1;
}

// ── Widget (small) ──────────────────────────────────────────────────

async function createWidget(sales) {
  const w = new ListWidget();
  drawGlassBackground(w);
  w.setPadding(14, 14, 14, 14);

  // ── Header row ──
  const header = w.addStack();
  header.layoutHorizontally();
  header.centerAlignContent();

  const dot = header.addText("\u25CF");  // filled circle
  dot.font = Font.systemFont(7);
  dot.textColor = new Color("#4ade80");  // green "live" dot

  header.addSpacer(5);

  const title = header.addText("Nature's Seed");
  title.font = Font.semiboldRoundedSystemFont(12);
  title.textColor = new Color("#d1fae5", 0.9);

  header.addSpacer(null);

  const live = header.addText("LIVE");
  live.font = Font.boldRoundedSystemFont(9);
  live.textColor = new Color("#4ade80", 0.7);

  w.addSpacer(8);

  // ── Revenue (hero number) ──
  const revLine = w.addText(fmt(sales.revenue));
  revLine.font = Font.boldRoundedSystemFont(34);
  revLine.textColor = Color.white();
  revLine.minimumScaleFactor = 0.5;

  w.addSpacer(2);

  const subtitle = w.addText("today's revenue");
  subtitle.font = Font.mediumRoundedSystemFont(11);
  subtitle.textColor = new Color("#86efac", 0.65);

  w.addSpacer(10);

  // ── Stat pills row ──
  const row = w.addStack();
  row.layoutHorizontally();
  row.spacing = 8;

  addStatPill(row, String(sales.orderCount), "orders");
  addStatPill(row, String(sales.units), "units");

  w.addSpacer(null);

  // ── Footer — last updated ──
  const footer = w.addStack();
  footer.layoutHorizontally();

  footer.addSpacer(null);

  const ts = footer.addText(fmtTime(new Date()));
  ts.font = Font.regularRoundedSystemFont(9);
  ts.textColor = new Color("#9ca3af", 0.5);

  // Refresh every 15 min
  w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000);
  return w;
}

// ── Medium widget (wider layout) ────────────────────────────────────

async function createMediumWidget(sales) {
  const w = new ListWidget();
  drawGlassBackground(w);
  w.setPadding(16, 18, 16, 18);

  // ── Header ──
  const header = w.addStack();
  header.layoutHorizontally();
  header.centerAlignContent();

  const dot = header.addText("\u25CF");
  dot.font = Font.systemFont(7);
  dot.textColor = new Color("#4ade80");

  header.addSpacer(5);

  const title = header.addText("Nature's Seed");
  title.font = Font.semiboldRoundedSystemFont(13);
  title.textColor = new Color("#d1fae5", 0.9);

  header.addSpacer(null);

  const badge = header.addText("LIVE");
  badge.font = Font.boldRoundedSystemFont(9);
  badge.textColor = new Color("#4ade80", 0.7);

  w.addSpacer(6);

  // ── Main content row ──
  const main = w.addStack();
  main.layoutHorizontally();
  main.centerAlignContent();

  // Left — Revenue
  const left = main.addStack();
  left.layoutVertically();

  const revText = left.addText(fmt(sales.revenue));
  revText.font = Font.boldRoundedSystemFont(38);
  revText.textColor = Color.white();
  revText.minimumScaleFactor = 0.5;

  left.addSpacer(2);

  const revLabel = left.addText("today's revenue");
  revLabel.font = Font.mediumRoundedSystemFont(12);
  revLabel.textColor = new Color("#86efac", 0.65);

  main.addSpacer(null);

  // Right — Stat pills stacked
  const right = main.addStack();
  right.layoutVertically();
  right.spacing = 6;

  addStatPill(right, String(sales.orderCount), "orders");
  addStatPill(right, String(sales.units), "units");

  w.addSpacer(null);

  // ── Footer ──
  const footer = w.addStack();
  footer.layoutHorizontally();
  footer.addSpacer(null);

  const ts = footer.addText(fmtTime(new Date()));
  ts.font = Font.regularRoundedSystemFont(9);
  ts.textColor = new Color("#9ca3af", 0.5);

  w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000);
  return w;
}

// ── Error widget ────────────────────────────────────────────────────

async function createErrorWidget(message) {
  const w = new ListWidget();
  drawGlassBackground(w);
  w.setPadding(16, 16, 16, 16);

  const title = w.addText("Nature's Seed");
  title.font = Font.semiboldRoundedSystemFont(13);
  title.textColor = new Color("#fca5a5");

  w.addSpacer(8);

  const err = w.addText(message);
  err.font = Font.regularRoundedSystemFont(12);
  err.textColor = new Color("#ffffff", 0.7);

  w.addSpacer(null);

  const hint = w.addText("Check API keys");
  hint.font = Font.regularRoundedSystemFont(10);
  hint.textColor = new Color("#9ca3af", 0.5);

  w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000);
  return w;
}

// ── Main ────────────────────────────────────────────────────────────

try {
  const sales = await getTodaySales();

  let widget;
  if (config.widgetFamily === "medium") {
    widget = await createMediumWidget(sales);
  } else {
    widget = await createWidget(sales);
  }

  if (config.runsInWidget) {
    Script.setWidget(widget);
  } else {
    await widget.presentSmall();
  }
} catch (e) {
  console.error(`Widget error: ${e}`);
  const widget = await createErrorWidget("Couldn't reach store");
  if (config.runsInWidget) {
    Script.setWidget(widget);
  } else {
    await widget.presentSmall();
  }
}

Script.complete();
