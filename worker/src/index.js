export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    if (method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    const authHeader = request.headers.get("X-API-Key");
    if (authHeader !== "blogdex-secret-key") {
      return json({ error: "Unauthorized" }, 401);
    }

    try {
      if (path === "/blogs" && method === "GET") {
        const { results } = await env.DB.prepare("SELECT * FROM blogs ORDER BY id").all();
        return json(results);
      }

      if (path === "/blogs" && method === "POST") {
        const body = await request.json();
        const { results } = await env.DB.prepare(
          "INSERT INTO blogs (name, platform, url, ga4_property_id) VALUES (?, ?, ?, ?) RETURNING *"
        ).bind(body.name, body.platform, body.url || "", body.ga4_property_id || "").all();
        return json(results[0]);
      }

      if (path === "/posts" && method === "POST") {
        const body = await request.json();
        const stmt = env.DB.prepare(
          "INSERT OR IGNORE INTO my_posts (blog_id, title, url, keywords, published_at) VALUES (?, ?, ?, ?, ?)"
        );
        const batch = body.posts.map(p =>
          stmt.bind(p.blog_id, p.title, p.url || "", p.keywords || "", p.published_at || "")
        );
        await env.DB.batch(batch);
        return json({ inserted: body.posts.length });
      }

      if (path === "/posts/search" && method === "GET") {
        const keyword = url.searchParams.get("q") || "";
        const pattern = "%" + keyword + "%";
        const { results } = await env.DB.prepare(
          "SELECT p.*, b.name as blog_name, b.platform FROM my_posts p JOIN blogs b ON p.blog_id = b.id WHERE p.title LIKE ? OR p.keywords LIKE ? ORDER BY p.published_at DESC LIMIT 10000"
        ).bind(pattern, pattern).all();
        return json({ results });
      }

      if (path === "/titles" && method === "POST") {
        const body = await request.json();
        const stmt = env.DB.prepare(
          "INSERT OR IGNORE INTO collected_titles (title, url, source, status) VALUES (?, ?, ?, 'new')"
        );
        const batch = body.titles.map(t => stmt.bind(t.title, t.url || "", t.source || ""));
        await env.DB.batch(batch);
        return json({ inserted: body.titles.length });
      }

      if (path === "/titles/search" && method === "GET") {
        const keyword = url.searchParams.get("q") || "";
        const status = url.searchParams.get("status") || "";
        let query = "SELECT * FROM collected_titles WHERE title LIKE ?";
        const binds = ["%" + keyword + "%"];
        if (status) { query += " AND status = ?"; binds.push(status); }
        query += " ORDER BY created_at DESC LIMIT 10000";
        const { results } = await env.DB.prepare(query).bind(...binds).all();
        return json({ results });
      }

      if (path === "/titles/status" && method === "PUT") {
        const body = await request.json();
        const stmt = env.DB.prepare("UPDATE collected_titles SET status = ? WHERE id = ?");
        const batch = body.updates.map(u => stmt.bind(u.status, u.id));
        await env.DB.batch(batch);
        return json({ updated: body.updates.length });
      }

      if (path === "/titles/stats" && method === "GET") {
        const { results } = await env.DB.prepare(
          "SELECT status, COUNT(*) as count FROM collected_titles GROUP BY status"
        ).all();
        return json({ results });
      }

      if (path === "/performance" && method === "POST") {
        const body = await request.json();
        const stmt = env.DB.prepare(
          "INSERT OR REPLACE INTO performance (post_id, date, pageviews, sessions, clicks, impressions) VALUES (?, ?, ?, ?, ?, ?)"
        );
        const batch = body.data.map(d => stmt.bind(d.post_id, d.date, d.pageviews || 0, d.sessions || 0, d.clicks || 0, d.impressions || 0));
        await env.DB.batch(batch);
        return json({ inserted: body.data.length });
      }

      if (path === "/performance" && method === "GET") {
        const days = url.searchParams.get("days") || "30";
        const { results } = await env.DB.prepare(
          "SELECT p.title, b.name as blog_name, b.platform, SUM(pf.pageviews) as total_views, SUM(pf.clicks) as total_clicks FROM performance pf JOIN my_posts p ON pf.post_id = p.id JOIN blogs b ON p.blog_id = b.id WHERE pf.date >= date('now', '-' || ? || ' days') GROUP BY p.id ORDER BY total_views DESC"
        ).bind(days).all();
        return json({ results });
      }

      if (path === "/gsc/daily" && method === "POST") {
        const body = await request.json();
        const stmt = env.DB.prepare(
          "INSERT OR REPLACE INTO gsc_daily (site, date, clicks, impressions, ctr) VALUES (?, ?, ?, ?, ?)"
        );
        const batch = body.data.map(d => stmt.bind(d.site, d.date, d.clicks || 0, d.impressions || 0, d.ctr || 0));
        await env.DB.batch(batch);
        return json({ inserted: body.data.length });
      }

      if (path === "/gsc/daily" && method === "GET") {
        const days = url.searchParams.get("days") || "30";
        const site = url.searchParams.get("site") || "";
        if (site) {
          const { results } = await env.DB.prepare(
            "SELECT * FROM gsc_daily WHERE site = ? AND date >= date('now', '-' || ? || ' days') ORDER BY date"
          ).bind(site, days).all();
          return json(results);
        }
        const { results } = await env.DB.prepare(
          "SELECT date, SUM(clicks) as clicks, SUM(impressions) as impressions, CASE WHEN SUM(impressions) > 0 THEN ROUND(SUM(clicks) * 100.0 / SUM(impressions), 2) ELSE 0 END as ctr FROM gsc_daily WHERE date >= date('now', '-' || ? || ' days') GROUP BY date ORDER BY date"
        ).bind(days).all();
        return json(results);
      }

      if (path === "/gsc/sites" && method === "GET") {
        const days = url.searchParams.get("days") || "30";
        const { results } = await env.DB.prepare(
          "SELECT site, SUM(clicks) as clicks, SUM(impressions) as impressions, CASE WHEN SUM(impressions) > 0 THEN ROUND(SUM(clicks) * 100.0 / SUM(impressions), 2) ELSE 0 END as ctr FROM gsc_daily WHERE date >= date('now', '-' || ? || ' days') GROUP BY site ORDER BY impressions DESC"
        ).bind(days).all();
        return json(results);
      }

      if (path === "/gsc/keywords" && method === "POST") {
        const body = await request.json();
        const stmt = env.DB.prepare(
          "INSERT OR REPLACE INTO gsc_keywords (site, date, query, clicks, impressions, ctr, position) VALUES (?, ?, ?, ?, ?, ?, ?)"
        );
        const items = body.data;
        for (let i = 0; i < items.length; i += 100) {
          const chunk = items.slice(i, i + 100);
          const batch = chunk.map(d => stmt.bind(d.site, d.date, d.query, d.clicks || 0, d.impressions || 0, d.ctr || 0, d.position || 0));
          await env.DB.batch(batch);
        }
        return json({ inserted: items.length });
      }

      if (path === "/gsc/keywords" && method === "GET") {
        const days = url.searchParams.get("days") || "30";
        const site = url.searchParams.get("site") || "";
        const limit = url.searchParams.get("limit") || "100";
        let query = "SELECT query, SUM(clicks) as clicks, SUM(impressions) as impressions, ROUND(AVG(position), 1) as avg_position, CASE WHEN SUM(impressions) > 0 THEN ROUND(SUM(clicks) * 100.0 / SUM(impressions), 2) ELSE 0 END as ctr FROM gsc_keywords WHERE date >= date('now', '-' || ? || ' days')";
        const binds = [days];
        if (site) { query += " AND site = ?"; binds.push(site); }
        query += " GROUP BY query ORDER BY impressions DESC LIMIT ?";
        binds.push(limit);
        const { results } = await env.DB.prepare(query).bind(...binds).all();
        return json(results);
      }

      if (path === "/gsc/keywords/trend" && method === "GET") {
        const q = url.searchParams.get("q") || "";
        const days = url.searchParams.get("days") || "30";
        if (!q) return json({ error: "q parameter required" }, 400);
        const { results } = await env.DB.prepare(
          "SELECT date, SUM(clicks) as clicks, SUM(impressions) as impressions, ROUND(AVG(position), 1) as avg_position FROM gsc_keywords WHERE query = ? AND date >= date('now', '-' || ? || ' days') GROUP BY date ORDER BY date"
        ).bind(q, days).all();
        return json(results);
      }

      if (path === "/coupang" && method === "POST") {
        const body = await request.json();
        const stmt = env.DB.prepare(
          "INSERT OR REPLACE INTO coupang_revenue (date, sub_id, clicks, orders, amount, revenue, product, source_file) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        );
        const items = body.data;
        for (let i = 0; i < items.length; i += 100) {
          const chunk = items.slice(i, i + 100);
          const batch = chunk.map(d => stmt.bind(d.date || "", d.sub_id || "", d.clicks || 0, d.orders || 0, d.amount || 0, d.revenue || 0, d.product || "", d.source_file || ""));
          await env.DB.batch(batch);
        }
        return json({ inserted: items.length });
      }

      if (path === "/coupang/summary" && method === "GET") {
        const days = url.searchParams.get("days") || "30";
        const { results } = await env.DB.prepare(
          "SELECT date, SUM(clicks) as clicks, SUM(orders) as orders, SUM(amount) as amount, SUM(revenue) as revenue FROM coupang_revenue WHERE date >= date('now', '-' || ? || ' days') GROUP BY date ORDER BY date"
        ).bind(days).all();
        const totals = await env.DB.prepare(
          "SELECT SUM(clicks) as clicks, SUM(orders) as orders, SUM(amount) as amount, SUM(revenue) as revenue FROM coupang_revenue WHERE date >= date('now', '-' || ? || ' days')"
        ).bind(days).first();
        return json({ daily: results, totals });
      }

      if (path === "/coupang/by-sub" && method === "GET") {
        const days = url.searchParams.get("days") || "30";
        const { results } = await env.DB.prepare(
          "SELECT sub_id, SUM(clicks) as clicks, SUM(orders) as orders, SUM(revenue) as revenue FROM coupang_revenue WHERE date >= date('now', '-' || ? || ' days') GROUP BY sub_id ORDER BY revenue DESC"
        ).bind(days).all();
        return json(results);
      }

      if (path === "/dashboard/summary" && method === "GET") {
        const days = url.searchParams.get("days") || "30";
        const blogs = await env.DB.prepare("SELECT COUNT(*) as count FROM blogs").first();
        const posts = await env.DB.prepare("SELECT COUNT(*) as count FROM my_posts").first();
        const titles = await env.DB.prepare("SELECT COUNT(*) as count FROM collected_titles").first();
        const gsc = await env.DB.prepare(
          "SELECT SUM(clicks) as clicks, SUM(impressions) as impressions FROM gsc_daily WHERE date >= date('now', '-' || ? || ' days')"
        ).bind(days).first();
        const coupang = await env.DB.prepare(
          "SELECT SUM(revenue) as revenue, SUM(orders) as orders FROM coupang_revenue WHERE date >= date('now', '-' || ? || ' days')"
        ).bind(days).first();
        return json({
          blogs: blogs?.count || 0,
          posts: posts?.count || 0,
          titles: titles?.count || 0,
          gsc_clicks: gsc?.clicks || 0,
          gsc_impressions: gsc?.impressions || 0,
          coupang_revenue: coupang?.revenue || 0,
          coupang_orders: coupang?.orders || 0,
          days: parseInt(days),
        });
      }

      return json({ error: "Not found" }, 404);
    } catch (e) {
      return json({ error: e.message }, 500);
    }
  }
};

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-API-Key"
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, X-API-Key"
    }
  });
}

