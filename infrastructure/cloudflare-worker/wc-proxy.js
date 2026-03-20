/**
 * Cloudflare Worker — WordPress API Proxy
 *
 * Bypasses Bot Fight Mode by running inside Cloudflare's network.
 * Supports both WooCommerce REST API (/wc/v3) and WordPress REST API (/wp/v2).
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
    // Allow GET, POST, PUT, PATCH, DELETE
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
      "Authorization": request.headers.get("Authorization"),
      "User-Agent": "NaturesSeed-CloudflareWorker/1.0",
      "Accept": "application/json",
    };

    // Forward body for write methods
    const fetchOptions = {
      method: request.method,
      headers: reqHeaders,
    };

    if (["POST", "PUT", "PATCH"].includes(request.method)) {
      reqHeaders["Content-Type"] = request.headers.get("Content-Type") || "application/json";
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
  },
};
