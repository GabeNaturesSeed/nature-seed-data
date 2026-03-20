// Nature's Seed — Daily Sales Widget for Scriptable (iOS)
// Frosted glass · WooCommerce · 15 min refresh
// Shows today's revenue + order count. Minimal API calls.

// ── Config ──────────────────────────────────────────────────────────
var WC_CK = "ck_9629579f1379f272169de8628edddb00b24737f9";
var WC_CS = "cs_bf6dcf206d6ed26b83e55e8af62c16de26339815";
// ────────────────────────────────────────────────────────────────────

async function fetchByStatus(status, after, before) {
  var base = "https://naturesseed.com/wp-json/wc/v3/orders";
  var auth = btoa(WC_CK + ":" + WC_CS);
  var all = [];
  var page = 1;

  while (true) {
    var url = base
      + "?status=" + status
      + "&after=" + after
      + "&before=" + before
      + "&per_page=100"
      + "&page=" + page;

    var req = new Request(url);
    req.headers = {
      "Authorization": "Basic " + auth,
      "User-Agent": "NaturesSeed-iPhoneWidget/1.0"
    };
    req.timeoutInterval = 30;

    var orders = await req.loadJSON();
    if (!Array.isArray(orders) || orders.length === 0) break;
    all = all.concat(orders);
    if (orders.length < 100) break;
    page++;
  }
  return all;
}

async function getTodaySales() {
  var now = new Date();
  var y = now.getFullYear();
  var m = String(now.getMonth() + 1).padStart(2, "0");
  var d = String(now.getDate()).padStart(2, "0");
  var after = y + "-" + m + "-" + d + "T00:00:00";
  var before = y + "-" + m + "-" + d + "T23:59:59";

  var completed = await fetchByStatus("completed", after, before);
  var processing = await fetchByStatus("processing", after, before);
  var all = completed.concat(processing);

  var revenue = 0;
  for (var i = 0; i < all.length; i++) {
    revenue += parseFloat(all[i].total || 0);
  }
  return { revenue: revenue, orderCount: all.length };
}

// ── Helpers ─────────────────────────────────────────────────────────

function fmt(n) {
  return "$" + n.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function fmtTime(d) {
  var h = d.getHours();
  var m = String(d.getMinutes()).padStart(2, "0");
  var ampm = h >= 12 ? "PM" : "AM";
  h = h % 12 || 12;
  return h + ":" + m + " " + ampm;
}

// ── Glass background ────────────────────────────────────────────────

function drawGlassBackground(w) {
  var g = new LinearGradient();
  g.locations = [0, 0.5, 1];
  g.colors = [
    new Color("#1a2f25", 0.85),
    new Color("#1e3a2c", 0.78),
    new Color("#162b20", 0.90),
  ];
  w.backgroundGradient = g;
}

// ── Small widget ────────────────────────────────────────────────────

function createWidget(sales) {
  var w = new ListWidget();
  drawGlassBackground(w);
  w.setPadding(14, 14, 14, 14);

  // Header
  var header = w.addStack();
  header.layoutHorizontally();
  header.centerAlignContent();

  var dot = header.addText("\u25CF");
  dot.font = Font.systemFont(7);
  dot.textColor = new Color("#4ade80");
  header.addSpacer(5);

  var title = header.addText("Nature's Seed");
  title.font = Font.semiboldRoundedSystemFont(12);
  title.textColor = new Color("#d1fae5", 0.9);
  header.addSpacer(null);

  var live = header.addText("LIVE");
  live.font = Font.boldRoundedSystemFont(9);
  live.textColor = new Color("#4ade80", 0.7);

  w.addSpacer(8);

  // Revenue
  var revLine = w.addText(fmt(sales.revenue));
  revLine.font = Font.boldRoundedSystemFont(34);
  revLine.textColor = Color.white();
  revLine.minimumScaleFactor = 0.5;

  w.addSpacer(2);

  var subtitle = w.addText("today's revenue");
  subtitle.font = Font.mediumRoundedSystemFont(11);
  subtitle.textColor = new Color("#86efac", 0.65);

  w.addSpacer(null);

  // Footer: orders + timestamp
  var footer = w.addStack();
  footer.layoutHorizontally();
  footer.centerAlignContent();

  var ordTxt = footer.addText(sales.orderCount + " orders");
  ordTxt.font = Font.mediumRoundedSystemFont(10);
  ordTxt.textColor = new Color("#a7f3d0", 0.7);

  footer.addSpacer(null);

  var ts = footer.addText(fmtTime(new Date()));
  ts.font = Font.regularRoundedSystemFont(9);
  ts.textColor = new Color("#9ca3af", 0.5);

  w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000);
  return w;
}

// ── Error widget ────────────────────────────────────────────────────

function createErrorWidget(message) {
  var w = new ListWidget();
  drawGlassBackground(w);
  w.setPadding(16, 16, 16, 16);

  var title = w.addText("Nature's Seed");
  title.font = Font.semiboldRoundedSystemFont(13);
  title.textColor = new Color("#fca5a5");

  w.addSpacer(8);

  var err = w.addText(message);
  err.font = Font.regularRoundedSystemFont(12);
  err.textColor = new Color("#ffffff", 0.7);

  w.addSpacer(null);

  var hint = w.addText("Tap to retry");
  hint.font = Font.regularRoundedSystemFont(10);
  hint.textColor = new Color("#9ca3af", 0.5);

  w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000);
  return w;
}

// ── Main ────────────────────────────────────────────────────────────

try {
  var sales = await getTodaySales();
  var widget = createWidget(sales);

  if (config.runsInWidget) {
    Script.setWidget(widget);
  } else {
    await widget.presentSmall();
  }
} catch (e) {
  var widget = createErrorWidget("Couldn't reach store");
  if (config.runsInWidget) {
    Script.setWidget(widget);
  } else {
    await widget.presentSmall();
  }
}

Script.complete();
