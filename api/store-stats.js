// store-stats.js — adds a GET /store-stats endpoint to your stellar-api.
//
// Why this exists: the dashboard runs in a browser and must NEVER hold the
// Shopify token. This runs on the server (where the token lives in .env),
// calls Shopify, caches the result, and returns clean numbers the dashboard
// can show. Browser -> your API -> Shopify. The token never leaves the server.
//
// INTEGRATE (pick one):
//   A)  In stellar-api's server.js, after `const app = express()`:
//         require("./store-stats")(app);
//   B)  Or paste the registerStoreStats body straight into server.js.
//
// REQUIRES:
//   - Node 18+ (uses global fetch — stellar-api is on Node, you're fine)
//   - SHOPIFY_SHOP and SHOPIFY_ACCESS_TOKEN in the SAME .env the OAuth script
//     wrote to (e.g. /root/stellar-station/.env). Make sure server.js loads it
//     (require("dotenv").config()).
//
// CROSS-ORIGIN NOTE: if the dashboard (:3000) and this API (:3001) are served
// from different ports/servers, the browser fetch is cross-origin. Easiest fix
// is to serve /store-stats from the SAME server that serves the dashboard so
// it's same-origin. Otherwise enable CORS on this route (uncomment below) and
// set STATS_URL in the dashboard to the full http://2.24.126.194:3001/store-stats.

const API_VERSION = "2026-04";
const TTL_MS = 10 * 60 * 1000; // 10-min cache — protects Shopify's rate limit

let _cache = null;
let _cacheTs = 0;

async function fetchStoreStats() {
  const shop = process.env.SHOPIFY_SHOP;          // getniella's .myshopify.com domain
  const token = process.env.SHOPIFY_ACCESS_TOKEN; // the shpat_ token from the OAuth step
  if (!shop || !token) {
    throw new Error("SHOPIFY_SHOP / SHOPIFY_ACCESS_TOKEN missing from .env");
  }

  const since = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10); // YYYY-MM-DD, 30 days ago

  const query = `{
    productsCount { count }
    products(first: 1, sortKey: UPDATED_AT, reverse: true) {
      edges { node { title totalInventory variants(first: 1) { edges { node { price } } } } }
    }
    orders(first: 100, sortKey: CREATED_AT, reverse: true, query: "created_at:>=${since}") {
      edges { node { currentTotalPriceSet { shopMoney { amount currencyCode } } } }
    }
  }`;

  const resp = await fetch(`https://${shop}/admin/api/${API_VERSION}/graphql.json`, {
    method: "POST",
    headers: { "X-Shopify-Access-Token": token, "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  const json = await resp.json();
  if (json.errors) {
    // If a field name is rejected by this API version, the error names it here.
    throw new Error("Shopify GraphQL error: " + JSON.stringify(json.errors));
  }

  const d = json.data || {};
  const orderEdges = (d.orders && d.orders.edges) || [];
  let revenue = 0;
  let currency = "USD";
  for (const e of orderEdges) {
    const m = e.node && e.node.currentTotalPriceSet && e.node.currentTotalPriceSet.shopMoney;
    if (m) {
      revenue += parseFloat(m.amount) || 0;
      currency = m.currencyCode || currency;
    }
  }
  const top = (d.products && d.products.edges && d.products.edges[0] && d.products.edges[0].node) || null;

  return {
    productCount:   (d.productsCount && d.productsCount.count) ?? null,
    orderCount30d:  orderEdges.length, // count of orders in the last 30 days (capped at 100)
    revenue30d:     Math.round(revenue * 100) / 100,
    currency,
    topProduct:     top ? top.title : null,
    topPrice:       top && top.variants && top.variants.edges[0] ? top.variants.edges[0].node.price : null,
    totalInventory: top ? top.totalInventory : null,
    updatedAt:      new Date().toISOString(),
  };
}

module.exports = function registerStoreStats(app) {
  app.get("/store-stats", async (req, res) => {
    res.set("Access-Control-Allow-Origin", "*");
    try {
      if (_cache && Date.now() - _cacheTs < TTL_MS) {
        return res.json(_cache);
      }
      _cache = await fetchStoreStats();
      _cacheTs = Date.now();
      res.json(_cache);
    } catch (err) {
      console.error("[store-stats]", err.message);
      if (_cache) return res.json({ ..._cache, stale: true }); // serve last good data on error
      res.status(502).json({ error: "shopify_fetch_failed", detail: err.message });
    }
  });
};
