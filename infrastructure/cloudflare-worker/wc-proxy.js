/**
 * Cloudflare Worker — WordPress API Proxy + WooCommerce Webhook Handler
 *
 * Routes:
 *   /webhook  — Receives WooCommerce "order.updated" webhooks, filters for
 *               status=completed, pushes tracking number + "Order Shipped"
 *               event to Klaviyo.
 *   /*        — Existing proxy that bypasses Bot Fight Mode for WC/WP API.
 *
 * Environment variables (set in CF Dashboard → Worker → Settings → Variables):
 *   PROXY_SECRET       — Shared secret for proxy auth (existing)
 *   WC_WEBHOOK_SECRET  — Secret set when creating the WC webhook
 *   KLAVIYO_PRIVATE_KEY — Klaviyo private API key (pk_...)
 *
 * Deploy:
 *   1. Go to Cloudflare Dashboard → Workers & Pages → wc-api-proxy
 *   2. Edit Code → paste this → Deploy
 *   3. Add WC_WEBHOOK_SECRET and KLAVIYO_PRIVATE_KEY as encrypted env vars
 *   4. Create webhook in WP Admin → WooCommerce → Settings → Advanced → Webhooks
 *      Topic: "Order updated", Delivery URL: https://wc-api-proxy.skylar-d51.workers.dev/webhook
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // --- Route: /webhook ---
    if (url.pathname === "/webhook") {
      return handleWebhook(request, env);
    }

    // --- Route: existing proxy (unchanged) ---
    return handleProxy(request, env);
  },
};

// ============================================================
// WEBHOOK HANDLER
// ============================================================

async function handleWebhook(request, env) {
  // Only accept POST
  if (request.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const rawBody = await request.text();

  // Debug logging — check in CF Dashboard → Workers → Logs
  const signature = request.headers.get("X-WC-Webhook-Signature");
  const topic = request.headers.get("X-WC-Webhook-Topic");
  console.log("WEBHOOK HIT", {
    topic,
    hasSignature: !!signature,
    hasSecret: !!env.WC_WEBHOOK_SECRET,
    bodyLength: rawBody.length,
    bodyPreview: rawBody.substring(0, 200),
  });

  // WooCommerce sends a bare verification ping (no signature headers)
  // when you first save the webhook — just return 200 to pass validation
  if (!signature) {
    console.log("Verification ping — no signature header, returning 200");
    return new Response("OK", { status: 200 });
  }

  // Validate WooCommerce HMAC signature on real deliveries
  if (!env.WC_WEBHOOK_SECRET) {
    console.log("REJECTED: WC_WEBHOOK_SECRET env var not set");
    return new Response("Unauthorized", { status: 401 });
  }

  const valid = await verifySignature(rawBody, signature, env.WC_WEBHOOK_SECRET);
  if (!valid) {
    console.log("REJECTED: signature mismatch", { signature });
    return new Response("Invalid signature", { status: 401 });
  }

  // Parse body
  let order;
  try {
    order = JSON.parse(rawBody);
  } catch {
    return new Response("Invalid JSON", { status: 400 });
  }

  // WooCommerce sends a ping on webhook creation — acknowledge it
  if (!topic || topic === "action.woocommerce_webhook_ping") {
    return new Response("Pong", { status: 200 });
  }

  // Only process completed orders
  if (order.status !== "completed") {
    return new Response("Ignored — not completed", { status: 200 });
  }

  // Extract tracking info from _wc_shipment_tracking_items
  const tracking = extractTracking(order);
  const email = order.billing?.email;

  if (!email) {
    return new Response("No billing email", { status: 200 });
  }

  // Build item names for the event
  const itemNames = (order.line_items || []).map((li) => li.name);
  const itemSkus = (order.line_items || []).map((li) => li.sku);

  // Call Klaviyo — update profile + track event
  try {
    await Promise.all([
      klaviyoUpdateProfile(env.KLAVIYO_PRIVATE_KEY, email, {
        tracking_number: tracking.number || "",
        tracking_carrier: tracking.carrier || "",
        last_shipped_order_id: order.id,
      }),
      klaviyoTrackEvent(env.KLAVIYO_PRIVATE_KEY, email, {
        OrderId: String(order.id),
        TrackingNumber: tracking.number || "",
        TrackingCarrier: tracking.carrier || "",
        TrackingLink: tracking.link || "",
        DateShipped: tracking.dateShipped || "",
        ItemNames: itemNames,
        ItemSkus: itemSkus,
        OrderTotal: parseFloat(order.total) || 0,
        CustomerFirstName: order.billing?.first_name || "",
      }, parseFloat(order.total) || 0),
    ]);
  } catch (err) {
    // Log but still return 200 so WC doesn't retry endlessly
    console.error("Klaviyo error:", err.message || err);
    return new Response(JSON.stringify({ ok: false, error: err.message }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(
    JSON.stringify({
      ok: true,
      order_id: order.id,
      email,
      tracking: tracking.number || "none",
    }),
    { status: 200, headers: { "Content-Type": "application/json" } }
  );
}

// --- Signature verification (HMAC-SHA256, base64) ---

async function verifySignature(body, signature, secret) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(body));
  const computed = btoa(String.fromCharCode(...new Uint8Array(sig)));
  return computed === signature;
}

// --- Extract tracking from WC Shipment Tracking plugin ---

function extractTracking(order) {
  const meta = order.meta_data || [];
  for (const m of meta) {
    if (m.key === "_wc_shipment_tracking_items" && Array.isArray(m.value) && m.value.length > 0) {
      const item = m.value[0]; // Take the first (most recent) tracking entry
      return {
        number: item.tracking_number || "",
        carrier: item.tracking_provider || "",
        link: item.custom_tracking_link || "",
        dateShipped: item.date_shipped || "",
      };
    }
  }
  return { number: "", carrier: "", link: "", dateShipped: "" };
}

// --- Klaviyo: update profile properties ---

async function klaviyoUpdateProfile(apiKey, email, properties) {
  const resp = await fetch("https://a.klaviyo.com/api/profile-import/", {
    method: "POST",
    headers: {
      Authorization: `Klaviyo-API-Key ${apiKey}`,
      "Content-Type": "application/json",
      revision: "2024-07-15",
    },
    body: JSON.stringify({
      data: {
        type: "profile",
        attributes: {
          email,
          properties,
        },
      },
    }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Klaviyo profile-import ${resp.status}: ${text}`);
  }
}

// --- Klaviyo: track "Order Shipped" event ---

async function klaviyoTrackEvent(apiKey, email, properties, value) {
  const resp = await fetch("https://a.klaviyo.com/api/events/", {
    method: "POST",
    headers: {
      Authorization: `Klaviyo-API-Key ${apiKey}`,
      "Content-Type": "application/json",
      revision: "2024-07-15",
    },
    body: JSON.stringify({
      data: {
        type: "event",
        attributes: {
          metric: {
            data: {
              type: "metric",
              attributes: { name: "Order Shipped" },
            },
          },
          profile: {
            data: {
              type: "profile",
              attributes: { email },
            },
          },
          properties,
          value,
          unique_id: `shipped-${properties.OrderId}`,
        },
      },
    }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Klaviyo events ${resp.status}: ${text}`);
  }
}

// ============================================================
// EXISTING PROXY HANDLER (unchanged)
// ============================================================

async function handleProxy(request, env) {
  const allowedMethods = ["GET", "POST", "PUT", "PATCH", "DELETE"];
  if (!allowedMethods.includes(request.method)) {
    return new Response("Method not allowed", { status: 405 });
  }

  // Validate secret token
  const authHeader = request.headers.get("X-Proxy-Secret");
  if (!authHeader || authHeader !== env.PROXY_SECRET) {
    return new Response("Unauthorized", { status: 401 });
  }

  const url = new URL(request.url);

  // Determine API base path: wp_path for WP REST API, wc_path for WC API
  const wpPath = url.searchParams.get("wp_path");
  const wcPath = url.searchParams.get("wc_path");

  let apiBase;
  let apiPath;
  if (wpPath) {
    apiBase = "https://naturesseed.com/wp-json/wp/v2";
    apiPath = wpPath;
  } else if (wcPath) {
    apiBase = "https://naturesseed.com/wp-json/wc/v3";
    apiPath = wcPath;
  } else {
    return new Response("Missing wc_path or wp_path parameter", { status: 400 });
  }

  // Build the origin URL — forward all other query params
  const originParams = new URLSearchParams(url.searchParams);
  originParams.delete("wc_path");
  originParams.delete("wp_path");

  const qs = originParams.toString();
  const originUrl = `${apiBase}${apiPath}${qs ? "?" + qs : ""}`;

  // Build request headers
  const reqHeaders = {
    Authorization: request.headers.get("Authorization"),
    "User-Agent": "NaturesSeed-CloudflareWorker/1.0",
    Accept: "application/json",
  };

  // Forward body for write methods
  const fetchOptions = {
    method: request.method,
    headers: reqHeaders,
  };

  if (["POST", "PUT", "PATCH"].includes(request.method)) {
    reqHeaders["Content-Type"] =
      request.headers.get("Content-Type") || "application/json";
    fetchOptions.body = await request.text();
  }

  // Forward the request
  const response = await fetch(originUrl, fetchOptions);

  // Return the response with relevant headers
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("Content-Type") || "application/json",
      "X-WP-TotalPages": response.headers.get("X-WP-TotalPages") || "1",
      "X-WP-Total": response.headers.get("X-WP-Total") || "0",
    },
  });
}
