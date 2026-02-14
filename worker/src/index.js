export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // CORS preflight
    if (method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    // 인증
    const authHeader = request.headers.get("X-API-Key");
    if (authHeader !== "blogdex-secret-key") {
      return json({ error: "Unauthorized" }, 401);
    }

    try {
      // 블로그 목록
      if (path === "/blogs" && method === "GET") {
        const { results } = await env.DB.prepare("SELECT * FROM blogs ORDER BY id").all();
        return json(results);
      }

      // 블로그 등록
      if (path === "/blogs" && method === "POST") {
        const body = await request.json();
        const { results } = await env.DB.prepare(
          "INSERT INTO blogs (name, platform, url, ga4_property_id) VALUES (?, ?, ?, ?) RETURNING *"
        ).bind(body.name, body.platform, body.url || "", body.ga4_property_id || "").all();
        return json(results[0]);
      }

      // 내 글 등록 (벌크)
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

      // 내 글 검색
      if (path === "/posts/search" && method === "GET") {
        const keyword = url.searchParams.get("q") || "";
        const pattern = `%${keyword}%`;
        const { results } = await env.DB.prepare(
          `SELECT p.*, b.name as blog_name, b.platform 
           FROM my_posts p JOIN blogs b ON p.blog_id = b.id 
           WHERE p.title LIKE ? OR p.keywords LIKE ? 
           ORDER BY p.published_at DESC LIMIT 10000`
        ).bind(pattern, pattern).all();
        return json({ results });
      }

      // 수집 타이틀 등록 (벌크)
      if (path === "/titles" && method === "POST") {
        const body = await request.json();
        const stmt = env.DB.prepare(
          "INSERT OR IGNORE INTO collected_titles (title, url, source, status) VALUES (?, ?, ?, 'new')"
        );
        const batch = body.titles.map(t =>
          stmt.bind(t.title, t.url || "", t.source || "")
        );
        await env.DB.batch(batch);
        return json({ inserted: body.titles.length });
      }

      // 수집 타이틀 검색
      if (path === "/titles/search" && method === "GET") {
        const keyword = url.searchParams.get("q") || "";
        const status = url.searchParams.get("status") || "";
        let query = "SELECT * FROM collected_titles WHERE title LIKE ?";
        const binds = [`%${keyword}%`];
        if (status) {
          query += " AND status = ?";
          binds.push(status);
        }
        query += " ORDER BY created_at DESC LIMIT 10000";
        const { results } = await env.DB.prepare(query).bind(...binds).all();
        return json({ results });
      }

      // 수집 타이틀 상태 변경
      if (path === "/titles/status" && method === "PUT") {
        const body = await request.json();
        const stmt = env.DB.prepare("UPDATE collected_titles SET status = ? WHERE id = ?");
        const batch = body.updates.map(u => stmt.bind(u.status, u.id));
        await env.DB.batch(batch);
        return json({ updated: body.updates.length });
      }

      // 수집 타이틀 통계
      if (path === "/titles/stats" && method === "GET") {
        const { results } = await env.DB.prepare(
          "SELECT status, COUNT(*) as count FROM collected_titles GROUP BY status"
        ).all();
        return json({ results });
      }

      // 수집 타이틀 vs 내 글 대조 (대량 분석)
      if (path === "/titles/analyze" && method === "GET") {
        const { results: titles } = await env.DB.prepare(
          "SELECT id, title FROM collected_titles WHERE status = 'new' LIMIT 1000"
        ).all();
        const duplicates = [];
        const fresh = [];
        for (const t of titles) {
          const words = t.title.split(/[\s,.\-\/]+/).filter(w => w.length >= 2);
          let found = false;
          for (const w of words.slice(0, 3)) {
            const { results: matches } = await env.DB.prepare(
              "SELECT id, title, blog_id FROM my_posts WHERE title LIKE ? LIMIT 1"
            ).bind(`%${w}%`).all();
            if (matches.length > 0) {
              duplicates.push({ title_id: t.id, title: t.title, matched_post: matches[0].title });
              found = true;
              break;
            }
          }
          if (!found) {
            fresh.push({ id: t.id, title: t.title });
          }
        }
        return json({ total: titles.length, duplicates: duplicates.length, fresh: fresh.length, fresh_titles: fresh.slice(0, 100), duplicate_titles: duplicates.slice(0, 100) });
      }

      // 퍼포먼스 저장 (벌크)
      if (path === "/performance" && method === "POST") {
        const body = await request.json();
        const stmt = env.DB.prepare(
          "INSERT OR REPLACE INTO performance (post_id, date, pageviews, sessions, clicks, impressions) VALUES (?, ?, ?, ?, ?, ?)"
        );
        const batch = body.data.map(d =>
          stmt.bind(d.post_id, d.date, d.pageviews || 0, d.sessions || 0, d.clicks || 0, d.impressions || 0)
        );
        await env.DB.batch(batch);
        return json({ inserted: body.data.length });
      }

      // 퍼포먼스 조회
      if (path === "/performance" && method === "GET") {
        const days = url.searchParams.get("days") || "30";
        const { results } = await env.DB.prepare(
          `SELECT p.title, b.name as blog_name, b.platform,
                  SUM(pf.pageviews) as total_views, SUM(pf.clicks) as total_clicks
           FROM performance pf
           JOIN my_posts p ON pf.post_id = p.id
           JOIN blogs b ON p.blog_id = b.id
           WHERE pf.date >= date('now', '-' || ? || ' days')
           GROUP BY p.id ORDER BY total_views DESC`
        ).bind(days).all();
        return json({ results });
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
