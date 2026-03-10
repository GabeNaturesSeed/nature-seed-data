/**
 * Cloudflare Worker — WooCommerce API Proxy
 *
 * Bypasses Bot Fight Mode by running inside Cloudflare's network.
 * GitHub Actions calls this Worker, which forwards to the WC REST API.
 *
 * Deploy:
 *   1. Go to Cloudflare Dashboard → Workers & Pages → Create Worker
 *   2. Paste this code → Deploy
 *   3. Add environment variable: PROXY_SECRET = <random secret>
 *   4. Add the same secret to GitHub repo secrets as CF_WORKER_SECRET
 *   5. Set the Worker URL in GitHub secrets as CF_WORKER_URL
 */

export default {
  async fetch(request, env) {
    // Only allow GET requests (WC API reads)
    if (request.method !== "GET") {
      return new Response("Method not allowed", { status: 405 });
    }

    // Validate secret token
    const authHeader = request.headers.get("X-Proxy-Secret");
    if (!authHeader || authHeader !== env.PROXY_SECRET) {
      return new Response("Unauthorized", { status: 401 });
    }

    // Get the WC API path from the request URL
    const url = new URL(request.url);
    const wcPath = url.searchParams.get("wc_path");
    if (!wcPath) {
      return new Response("Missing wc_path parameter", { status: 400 });
    }

    // Build the origin URL — forward all other query params
    const originParams = new URLSearchParams(url.searchParams);
    originParams.delete("wc_path");

    const originUrl = `https://naturesseed.com/wp-json/wc/v3${wcPath}?${originParams.toString()}`;

    // Forward the request to WooCommerce with Basic Auth
    const response = await fetch(originUrl, {
      method: "GET",
      headers: {
        "Authorization": request.headers.get("Authorization"),
        "User-Agent": "NaturesSeed-CloudflareWorker/1.0",
        "Accept": "application/json",
      },
    });

    // Return the response with CORS headers
    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "application/json",
        "X-WP-TotalPages": response.headers.get("X-WP-TotalPages") || "1",
        "X-WP-Total": response.headers.get("X-WP-Total") || "0",
      },
    });
  },
};
