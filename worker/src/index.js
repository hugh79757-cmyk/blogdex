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
      // === 키워드 스카우트: 네이버 블로그 검색 프록시 ===
      if (path === "/scout" && method === "GET") {
        const query = url.searchParams.get("q");
        const display = url.searchParams.get("display") || "3";
        if (!query) return json({ error: "q parameter required" }, 400);
        const cid = env.NAVER_CLIENT_ID;
        const csec = env.NAVER_CLIENT_SECRET;
        if (!cid || !csec) return json({ error: "Naver API keys not configured", has_id: !!cid, has_secret: !!csec }, 500);
        const naverUrl = "https://openapi.naver.com/v1/search/blog.json?" +
          new URLSearchParams({ query, display, sort: "sim" });
        const naverRes = await fetch(naverUrl, {
          headers: {
            "X-Naver-Client-Id": env.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": env.NAVER_CLIENT_SECRET
          }
        });
        const naverData = await naverRes.json();
        if (naverData.items && naverData.items.length > 0) {
          const stmt = env.DB.prepare(
            "INSERT OR IGNORE INTO collected_titles (title, url, source, status) VALUES (?, ?, ?, 'new')"
          );
          const batch = naverData.items.map(item => {
            const title = item.title.replace(/<[^>]+>/g, "").trim();
            return stmt.bind(title, item.link || "", "scout:" + query);
          });
          try { await env.DB.batch(batch); } catch(e) { /* ignore dup */ }
        }
        return json(naverData);
      }

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

      // 포스트 URL 벌크 업데이트
      if (path === "/posts/update-urls" && method === "POST") {
        const body = await request.json();
        const updates = body.updates || [];
        const stmt = env.DB.prepare(
          "UPDATE my_posts SET url = ? WHERE blog_id = ? AND title = ?"
        );
        const batch = updates.map(u => stmt.bind(u.url, u.blog_id, u.title));
        if (batch.length > 0) {
          // D1 batch 최대 100개씩
          for (let i = 0; i < batch.length; i += 100) {
            await env.DB.batch(batch.slice(i, i + 100));
          }
        }
        return json({ updated: updates.length });
      }

      if (path === "/posts/search" && method === "GET") {
        const keyword = url.searchParams.get("q") || "";
        const blogId = url.searchParams.get("blog_id") || "";
        const pattern = "%" + keyword + "%";
        let sql = "SELECT p.*, b.name as blog_name, b.platform FROM my_posts p JOIN blogs b ON p.blog_id = b.id WHERE (p.title LIKE ? OR p.keywords LIKE ?)";
        const binds = [pattern, pattern];
        if (blogId) {
          sql += " AND p.blog_id = ?";
          binds.push(parseInt(blogId));
        }
        sql += " ORDER BY p.published_at DESC LIMIT 10000";
        const { results } = await env.DB.prepare(sql).bind(...binds).all();
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
        const q = url.searchParams.get("q") || "";
        const { results } = await env.DB.prepare(
          "SELECT * FROM collected_titles WHERE title LIKE ? ORDER BY id DESC LIMIT 50"
        ).bind('%' + q + '%').all();
        
        // 각 타이틀에 대해 발행된 블로그 정보 매칭
        const enriched = [];
        for (const t of results) {
          const words = t.title.split(/\s+/).filter(w => w.length >= 2).slice(0, 3);
          let matchedBlogs = [];
          for (const w of words) {
            const { results: posts } = await env.DB.prepare(
              "SELECT p.title, p.url, b.name as blog_name, b.platform FROM my_posts p JOIN blogs b ON p.blog_id = b.id WHERE p.title LIKE ? LIMIT 5"
            ).bind('%' + w + '%').all();
            matchedBlogs.push(...posts);
          }
          const seen = new Set();
          const unique = matchedBlogs.filter(p => {
            const k = p.url || p.title;
            if (seen.has(k)) return false;
            seen.add(k); return true;
          });
          // 2개 이상 키워드 매칭된 것만
          const filtered = unique.filter(p => {
            const matched = words.filter(w => p.title && p.title.includes(w)).length;
            return matched >= 2;
          }).slice(0, 3);
          enriched.push({ ...t, published_in: filtered });
        }
        return json(enriched);
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
          "INSERT OR REPLACE INTO gsc_keywords (site, date, query, page, clicks, impressions, ctr, position) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        );
        const items = body.data;
        for (let i = 0; i < items.length; i += 100) {
          const chunk = items.slice(i, i + 100);
          const batch = chunk.map(d => stmt.bind(d.site, d.date, d.query, d.page || "", d.clicks || 0, d.impressions || 0, d.ctr || 0, d.position || 0));
          await env.DB.batch(batch);
        }
        return json({ inserted: items.length });
      }

      if (path === "/gsc/keywords" && method === "GET") {
        const days = parseInt(url.searchParams.get("days") || "30");
        const since = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
        const { results } = await env.DB.prepare(
          "SELECT query, site, SUM(clicks) as clicks, SUM(impressions) as impressions, AVG(position) as avg_position FROM gsc_keywords WHERE date >= ? GROUP BY query, site ORDER BY impressions DESC LIMIT 500"
        ).bind(since).all();
        const enriched = [];
        for (const r of results) {
          let blog_name = r.site || '';
          try {
            const host = new URL(r.site || 'http://x').hostname.replace('www.','');
            const { results: blogs } = await env.DB.prepare("SELECT name FROM blogs WHERE url LIKE ? LIMIT 1").bind('%' + host + '%').all();
            if (blogs.length > 0) blog_name = blogs[0].name;
            else blog_name = host;
          } catch(e) { blog_name = r.site || '-'; }
          const ctr = r.impressions > 0 ? Math.round(r.clicks / r.impressions * 10000) / 100 : 0;
          enriched.push({ query: r.query, site: r.site, blog_name, clicks: r.clicks, impressions: r.impressions, avg_position: Math.round((r.avg_position || 0) * 10) / 10, ctr });
        }
        return json(enriched);
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

      
      // --- 타이틀 발행 블로그 매칭 ---
      if (path === "/titles/match" && method === "POST") {
        const body = await request.json();
        const titles = body.titles || [];
        const results = [];
        for (const t of titles) {
          const words = t.split(/\s+/).filter(w => w.length >= 2).slice(0, 5);
          let posts = [];
          for (const w of words) {
            const { results: found } = await env.DB.prepare(
              "SELECT p.title, p.url, p.published_at, p.keywords, b.name as blog_name, b.url as blog_url FROM my_posts p JOIN blogs b ON p.blog_id = b.id WHERE p.title LIKE ? LIMIT 20"
            ).bind('%' + w + '%').all();
            posts.push(...found);
          }
          const seen = new Set();
          const unique = posts.filter(p => {
            const key = p.url || p.title;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
          });
          const matchCount = {};
          for (const p of unique) {
            const matched = words.filter(w => p.title && p.title.includes(w)).length;
            matchCount[p.url || p.title] = matched;
          }
          const sorted = unique.sort((a, b) => (matchCount[b.url || b.title] || 0) - (matchCount[a.url || a.title] || 0)).slice(0, 5);
          results.push({ title: t, published: sorted });
        }
        return json(results);
      }

      // --- 타이틀 최적 블로그 추천 ---
      if (path === "/titles/recommend" && method === "POST") {
        const body = await request.json();
        const titles = body.titles || [];
        const { results: blogs } = await env.DB.prepare("SELECT * FROM blogs").all();
        const results = [];
        for (const t of titles) {
          const stopWords = ['2024','2025','2026','그리고','하는','에서','으로','위한','대한','이란','what','the','how','총정리'];
          const words = t.split(/\s+/).filter(w => w.length >= 2 && !stopWords.includes(w)).slice(0, 6);
          if (words.length === 0) { results.push({ title: t, recommendation: null, reason: "키워드 추출 불가" }); continue; }
          const blogScores = {};
          for (const b of blogs) { blogScores[b.id] = { blog_name: b.name, blog_url: b.url, platform: b.platform, score: 0, impressions: 0, clicks: 0, reasons: [] }; }
          for (const w of words) {
            const { results: kwData } = await env.DB.prepare("SELECT site, SUM(impressions) as imp, SUM(clicks) as clk FROM gsc_keywords WHERE query LIKE ? GROUP BY site").bind('%' + w + '%').all();
            for (const kw of kwData) {
              for (const b of blogs) {
                try {
                  const host = new URL(b.url || 'http://x').hostname;
                  if (kw.site && kw.site.includes(host)) {
                    blogScores[b.id].score += (kw.imp || 0) * 2 + (kw.clk || 0) * 10;
                    blogScores[b.id].impressions += kw.imp || 0;
                    blogScores[b.id].clicks += kw.clk || 0;
                    blogScores[b.id].reasons.push(w + ':' + (kw.imp||0) + '노출');
                  }
                } catch(e) {}
              }
            }
          }
          const dupCount = {};
          for (const w of words) {
            const { results: dups } = await env.DB.prepare("SELECT blog_id, COUNT(*) as cnt FROM my_posts WHERE title LIKE ? GROUP BY blog_id").bind('%' + w + '%').all();
            for (const d of dups) { dupCount[d.blog_id] = (dupCount[d.blog_id] || 0) + d.cnt; }
          }
          const ranked = Object.values(blogScores).map(bs => {
            const bid = blogs.find(b => b.name === bs.blog_name)?.id;
            const penalty = (dupCount[bid] || 0) * 5;
            return { ...bs, dup_count: dupCount[bid] || 0, final_score: bs.score - penalty };
          }).sort((a, b) => b.final_score - a.final_score);
          const top = ranked[0];
          results.push({ title: t, recommendation: top.blog_name, blog_url: top.blog_url, score: top.final_score, impressions: top.impressions, clicks: top.clicks, dup_count: top.dup_count, reasons: top.reasons.slice(0, 5), all_blogs: ranked.slice(0, 3) });
        }
        return json(results);
      }

      // --- 타이틀 상태 일괄 업데이트 ---
      if (path === "/titles/bulk-status" && method === "PUT") {
        const body = await request.json();
        const ids = body.ids || [];
        const status = body.status || "saved";
        if (ids.length === 0) return json({ updated: 0 });
        let updated = 0;
        for (const id of ids) {
          await env.DB.prepare("UPDATE collected_titles SET status = ? WHERE id = ?").bind(status, id).run();
          updated++;
        }
        return json({ updated });
      }

      
      // --- 출처 목록 ---
      if (path === "/titles/sources" && method === "GET") {
        const { results } = await env.DB.prepare("SELECT source, COUNT(*) as count FROM collected_titles GROUP BY source ORDER BY count DESC").all();
        return json(results);
      }

// --- 타이틀 필터 조회 (status별) ---
      if (path === "/titles/filter" && method === "GET") {
        const status = url.searchParams.get("status") || "all";
        const page = parseInt(url.searchParams.get("page") || "1");
        const limit = parseInt(url.searchParams.get("limit") || "50");
        const offset = (page - 1) * limit;
        let rows, countRow;
        const source = url.searchParams.get("source") || "";
        if (status === "all" && !source) {
          countRow = await env.DB.prepare("SELECT COUNT(*) as total FROM collected_titles").first();
          const { results } = await env.DB.prepare("SELECT * FROM collected_titles ORDER BY id DESC LIMIT ? OFFSET ?").bind(limit, offset).all();
          rows = results;
        } else if (status === "all" && source) {
          countRow = await env.DB.prepare("SELECT COUNT(*) as total FROM collected_titles WHERE source = ?").bind(source).first();
          const { results } = await env.DB.prepare("SELECT * FROM collected_titles WHERE source = ? ORDER BY id DESC LIMIT ? OFFSET ?").bind(source, limit, offset).all();
          rows = results;
        } else if (status !== "all" && !source) {
          countRow = await env.DB.prepare("SELECT COUNT(*) as total FROM collected_titles WHERE status = ?").bind(status).first();
          const { results } = await env.DB.prepare("SELECT * FROM collected_titles WHERE status = ? ORDER BY id DESC LIMIT ? OFFSET ?").bind(status, limit, offset).all();
          rows = results;
        } else {
          countRow = await env.DB.prepare("SELECT COUNT(*) as total FROM collected_titles WHERE status = ? AND source = ?").bind(status, source).first();
          const { results } = await env.DB.prepare("SELECT * FROM collected_titles WHERE status = ? AND source = ? ORDER BY id DESC LIMIT ? OFFSET ?").bind(status, source, limit, offset).all();
          rows = results;
        }
        return json({ total: countRow?.total || 0, page, limit, data: rows });
      }

      // --- 타이틀 상세 (클릭시 정보) ---
      if (path.startsWith("/titles/detail/") && method === "GET") {
        const titleId = path.split("/titles/detail/")[1];
        const { results: titleRows } = await env.DB.prepare("SELECT * FROM collected_titles WHERE id = ?").bind(titleId).all();
        if (titleRows.length === 0) return json({ error: "Not found" }, 404);
        return json(titleRows[0]);
      }

    if (path === "/ga4/pageviews" && method === "POST") {
      const body = await request.json();
      const data = body.data || [];
      if (data.length === 0) return json({ inserted: 0 });
      const stmt = env.DB.prepare(
        "INSERT OR REPLACE INTO ga4_pageviews (site, date, page, pageviews, sessions, revenue) VALUES (?, ?, ?, ?, ?, ?)"
      );
      const chunks = [];
      for (let i = 0; i < data.length; i += 50) {
        chunks.push(data.slice(i, i + 50));
      }
      let total = 0;
      for (const chunk of chunks) {
        const batch = chunk.map(d => stmt.bind(d.site, d.date, d.page, d.pageviews || 0, d.sessions || 0, d.revenue || 0));
        await env.DB.batch(batch);
        total += chunk.length;
      }
      return json({ inserted: total });
    }

    
    // === 수익 기회 분석 ===
    if (path === "/analysis/rewrite-targets" && method === "GET") {
      const { results } = await env.DB.prepare(
        "SELECT page, site, SUM(impressions) as imp, SUM(clicks) as clk, ROUND(AVG(position),1) as pos, GROUP_CONCAT(DISTINCT query) as queries FROM gsc_keywords WHERE page != '' GROUP BY page HAVING imp >= 10 AND clk = 0 ORDER BY imp DESC LIMIT 30"
      ).all();
      return json(results);
    }

    if (path === "/analysis/top-pages" && method === "GET") {
      const { results } = await env.DB.prepare(
        "SELECT site, page, SUM(pageviews) as pv, SUM(sessions) as sess FROM ga4_pageviews GROUP BY site, page ORDER BY pv DESC LIMIT 30"
      ).all();
      return json(results);
    }

    if (path === "/analysis/seo-opportunity" && method === "GET") {
      const { results: ga4Top } = await env.DB.prepare(
        "SELECT site, page, SUM(pageviews) as pv FROM ga4_pageviews GROUP BY site, page HAVING pv >= 10 ORDER BY pv DESC LIMIT 200"
      ).all();
      const { results: gscPages } = await env.DB.prepare(
        "SELECT DISTINCT page FROM gsc_keywords WHERE page != ''"
      ).all();
      const gscSet = new Set(gscPages.map(r => r.page));
      const opportunities = ga4Top.filter(r => !gscSet.has(r.page)).slice(0, 30);
      return json(opportunities);
    }

    if (path === "/analysis/blog-efficiency" && method === "GET") {
      const { results } = await env.DB.prepare(
        "SELECT g.site, SUM(g.pageviews) as total_pv, COUNT(DISTINCT g.page) as pages, ROUND(1.0 * SUM(g.pageviews) / COUNT(DISTINCT g.page), 1) as pv_per_page FROM ga4_pageviews g GROUP BY g.site ORDER BY pv_per_page DESC"
      ).all();
      return json(results);
    }

    
    if (path === "/analysis/rpm-ranking" && method === "GET") {
      const { results } = await env.DB.prepare(
        `SELECT site, page, 
         SUM(pageviews) as pv, 
         SUM(revenue) as rev,
         ROUND(SUM(revenue) / SUM(pageviews) * 1000, 2) as rpm
         FROM ga4_pageviews 
         WHERE pageviews > 0
         GROUP BY site, page 
         HAVING rev > 0
         ORDER BY rpm DESC 
         LIMIT 50`
      ).all();
      return json(results);
    }

    if (path === "/analysis/revenue-summary" && method === "GET") {
      // 오늘 / 어제 / 7일평균 / 이번달 누적
      const { results: daily30 } = await env.DB.prepare(
        "SELECT date, SUM(pageviews) as pv, SUM(revenue) as rev FROM ga4_pageviews GROUP BY date ORDER BY date DESC LIMIT 30"
      ).all();

      const today     = daily30[0] || {};
      const yesterday = daily30[1] || {};
      const avg7      = daily30.slice(0, 7).reduce((s,d) => s + (d.rev||0), 0) / Math.min(7, daily30.length);
      const avg7pv    = daily30.slice(0, 7).reduce((s,d) => s + (d.pv||0),  0) / Math.min(7, daily30.length);

      const thisMonth = (today.date || "").substring(0, 7);
      const monthRows = daily30.filter(d => (d.date||"").startsWith(thisMonth));
      const monthRev  = monthRows.reduce((s,d) => s + (d.rev||0), 0);

      const todayRpm  = today.pv  > 0 ? Math.round(today.rev  / today.pv  * 1000 * 100) / 100 : 0;
      const yesterRpm = yesterday.pv > 0 ? Math.round(yesterday.rev / yesterday.pv * 1000 * 100) / 100 : 0;

      // TOP 3 사이트 (오늘)
      const { results: topSites } = await env.DB.prepare(
        "SELECT site, SUM(pageviews) as pv, SUM(revenue) as rev, ROUND(SUM(revenue)/SUM(pageviews)*1000,2) as rpm FROM ga4_pageviews WHERE date = ? GROUP BY site ORDER BY rev DESC LIMIT 3"
      ).bind(today.date || "").all();

      // 수익 0 사이트 (최근 7일, pv>=50)
      const { results: zeroSites } = await env.DB.prepare(
        "SELECT site, SUM(pageviews) as pv, SUM(revenue) as rev FROM ga4_pageviews WHERE date >= date('now', '-7 days') GROUP BY site HAVING pv >= 50 AND rev = 0"
      ).all();

      return json({
        today_revenue:     Math.round((today.rev     || 0) * 100) / 100,
        yesterday_revenue: Math.round((yesterday.rev || 0) * 100) / 100,
        avg7_revenue:      Math.round(avg7  * 100) / 100,
        month_revenue:     Math.round(monthRev * 100) / 100,
        today_rpm:         todayRpm,
        yesterday_rpm:     yesterRpm,
        today_pv:          today.pv     || 0,
        yesterday_pv:      yesterday.pv || 0,
        avg7_pv:           Math.round(avg7pv),
        top_sites:         topSites,
        zero_revenue_sites: zeroSites,
        daily_revenue:     daily30.slice(0, 7),
      });
    }

    
    if (path === "/coaching/today" && method === "GET") {
      // 1) 이번 달 수익 + 일별 수익
      const { results: dailyRev } = await env.DB.prepare(
        "SELECT date, SUM(pageviews) as pv, SUM(revenue) as rev FROM ga4_pageviews GROUP BY date ORDER BY date DESC LIMIT 30"
      ).all();

      // 2) 사이트별 수익 요약
      const { results: siteRev } = await env.DB.prepare(
        "SELECT site, SUM(pageviews) as pv, SUM(revenue) as rev, COUNT(DISTINCT page) as pages, COUNT(DISTINCT date) as days FROM ga4_pageviews WHERE date >= date('now', '-30 days') AND (revenue > 0 OR pageviews > 0) GROUP BY site ORDER BY rev DESC"
      ).all();

      // 3) 어제 vs 그저께 비교 (사이트별)
      const dates = dailyRev.map(d => d.date).slice(0, 2);
      let yesterdayData = [], beforeData = [];
      if (dates.length >= 2) {
        const { results: y } = await env.DB.prepare(
          "SELECT site, SUM(pageviews) as pv, SUM(revenue) as rev FROM ga4_pageviews WHERE date = ? GROUP BY site"
        ).bind(dates[0]).all();
        yesterdayData = y;
        const { results: b } = await env.DB.prepare(
          "SELECT site, SUM(pageviews) as pv, SUM(revenue) as rev FROM ga4_pageviews WHERE date = ? GROUP BY site"
        ).bind(dates[1]).all();
        beforeData = b;
      }

      // 4) 타이틀 리라이트 대상 TOP 10
      const { results: rewriteTargets } = await env.DB.prepare(
        "SELECT site, query, page, SUM(impressions) as imp, ROUND(AVG(position),1) as pos FROM gsc_keywords WHERE date >= date('now', '-30 days') AND page != '' AND impressions >= 3 GROUP BY site, query, page HAVING SUM(clicks) = 0 AND AVG(position) BETWEEN 3 AND 25 ORDER BY imp DESC LIMIT 10"
      ).all();

      // 5) RPM 상위 키워드 (경쟁사 리서치 가이드용)
      const { results: topRpm } = await env.DB.prepare(
        "SELECT g.site, g.page, SUM(g.pageviews) as pv, SUM(g.revenue) as rev, ROUND(SUM(g.revenue)/SUM(g.pageviews)*1000,2) as rpm FROM ga4_pageviews g WHERE g.date >= date('now', '-30 days') AND g.pageviews >= 5 AND g.revenue > 0 GROUP BY g.site, g.page ORDER BY rpm DESC LIMIT 10"
      ).all();

      // 6) 수익 0 사이트 (최근 7일 기준)
      const { results: recent7d } = await env.DB.prepare(
        "SELECT site, SUM(pageviews) as pv, SUM(revenue) as rev FROM ga4_pageviews WHERE date >= date('now', '-7 days') GROUP BY site HAVING pv >= 50 AND rev = 0"
      ).all();
      const zeroRev = recent7d;

      // 목표 계산
      const thisMonth = dailyRev.filter(d => d.date.startsWith(dates[0]?.substring(0,7) || ''));
      const monthRev = thisMonth.reduce((sum, d) => sum + (d.rev || 0), 0);
      const monthDays = thisMonth.length;
      const monthTarget = 300; // $300 목표
      const dailyNeeded = monthDays > 0 ? (monthTarget - monthRev) / (30 - monthDays) : 10;

      return json({
        summary: {
          month_revenue: Math.round(monthRev * 100) / 100,
          month_target: monthTarget,
          month_progress: Math.round(monthRev / monthTarget * 100),
          month_days: monthDays,
          daily_avg: Math.round(monthRev / (monthDays || 1) * 100) / 100,
          daily_needed: Math.round(dailyNeeded * 100) / 100,
          yesterday_rev: dailyRev[0]?.rev || 0,
          yesterday_pv: dailyRev[0]?.pv || 0,
        },
        daily_revenue: dailyRev,
        site_summary: siteRev,
        yesterday_compare: { yesterday: yesterdayData, before: beforeData },
        rewrite_targets: rewriteTargets,
        top_rpm_pages: topRpm,
        zero_revenue_sites: zeroRev,
      });
    }

    
    // === sync_log 엔드포인트 ===
    if (path === "/sync/log" && method === "POST") {
      // 1) 이번 달 수익 + 일별 수익
      const { results: dailyRev } = await env.DB.prepare(
        "SELECT date, SUM(pageviews) as pv, SUM(revenue) as rev FROM ga4_pageviews GROUP BY date ORDER BY date DESC LIMIT 30"
      ).all();

      // 2) 사이트별 수익 요약
      const { results: siteRev } = await env.DB.prepare(
        "SELECT site, SUM(pageviews) as pv, SUM(revenue) as rev, COUNT(DISTINCT page) as pages, COUNT(DISTINCT date) as days FROM ga4_pageviews WHERE date >= date('now', '-30 days') AND (revenue > 0 OR pageviews > 0) GROUP BY site ORDER BY rev DESC"
      ).all();

      // 3) 어제 vs 그저께 비교 (사이트별)
      const dates = dailyRev.map(d => d.date).slice(0, 2);
      let yesterdayData = [], beforeData = [];
      if (dates.length >= 2) {
        const { results: y } = await env.DB.prepare(
          "SELECT site, SUM(pageviews) as pv, SUM(revenue) as rev FROM ga4_pageviews WHERE date = ? GROUP BY site"
        ).bind(dates[0]).all();
        yesterdayData = y;
        const { results: b } = await env.DB.prepare(
          "SELECT site, SUM(pageviews) as pv, SUM(revenue) as rev FROM ga4_pageviews WHERE date = ? GROUP BY site"
        ).bind(dates[1]).all();
        beforeData = b;
      }

      // 4) 타이틀 리라이트 대상 TOP 10
      const { results: rewriteTargets } = await env.DB.prepare(
        "SELECT site, query, page, SUM(impressions) as imp, ROUND(AVG(position),1) as pos FROM gsc_keywords WHERE date >= date('now', '-30 days') AND page != '' AND impressions >= 3 GROUP BY site, query, page HAVING SUM(clicks) = 0 AND AVG(position) BETWEEN 3 AND 25 ORDER BY imp DESC LIMIT 10"
      ).all();

      // 5) RPM 상위 키워드 (경쟁사 리서치 가이드용)
      const { results: topRpm } = await env.DB.prepare(
        "SELECT g.site, g.page, SUM(g.pageviews) as pv, SUM(g.revenue) as rev, ROUND(SUM(g.revenue)/SUM(g.pageviews)*1000,2) as rpm FROM ga4_pageviews g WHERE g.date >= date('now', '-30 days') AND g.pageviews >= 5 AND g.revenue > 0 GROUP BY g.site, g.page ORDER BY rpm DESC LIMIT 10"
      ).all();

      // 6) 수익 0 사이트 (최근 7일 기준)
      const { results: recent7d } = await env.DB.prepare(
        "SELECT site, SUM(pageviews) as pv, SUM(revenue) as rev FROM ga4_pageviews WHERE date >= date('now', '-7 days') GROUP BY site HAVING pv >= 50 AND rev = 0"
      ).all();
      const zeroRev = recent7d;

      // 목표 계산
      const thisMonth = dailyRev.filter(d => d.date.startsWith(dates[0]?.substring(0,7) || ''));
      const monthRev = thisMonth.reduce((sum, d) => sum + (d.rev || 0), 0);
      const monthDays = thisMonth.length;
      const monthTarget = 300; // $300 목표
      const dailyNeeded = monthDays > 0 ? (monthTarget - monthRev) / (30 - monthDays) : 10;

      return json({
        summary: {
          month_revenue: Math.round(monthRev * 100) / 100,
          month_target: monthTarget,
          month_progress: Math.round(monthRev / monthTarget * 100),
          month_days: monthDays,
          daily_avg: Math.round(monthRev / (monthDays || 1) * 100) / 100,
          daily_needed: Math.round(dailyNeeded * 100) / 100,
          yesterday_rev: dailyRev[0]?.rev || 0,
          yesterday_pv: dailyRev[0]?.pv || 0,
        },
        daily_revenue: dailyRev,
        site_summary: siteRev,
        yesterday_compare: { yesterday: yesterdayData, before: beforeData },
        rewrite_targets: rewriteTargets,
        top_rpm_pages: topRpm,
        zero_revenue_sites: zeroRev,
      });
    }

    
    // === sync_log 엔드포인트 ===
    if (path === "/sync/log" && method === "POST") {
      const body = await request.json();
      const rows = body.logs || [body];
      for (const log of rows) {
        await env.DB.prepare(
          "INSERT INTO sync_log (source, site, last_synced_at, last_date_covered, row_count, status, message) VALUES (?, ?, ?, ?, ?, ?, ?)"
        ).bind(
          log.source, log.site || null, log.last_synced_at,
          log.last_date_covered || null, log.row_count || 0,
          log.status || "ok", log.message || null
        ).run();
      }
      return json({ ok: true, count: rows.length });
    }

    if (path === "/sync/log" && method === "GET") {
      const source = url.searchParams.get("source");
      let query = "SELECT * FROM sync_log";
      const params = [];
      if (source) {
        query += " WHERE source = ?";
        params.push(source);
      }
      query += " ORDER BY last_synced_at DESC LIMIT 50";
      const { results } = await env.DB.prepare(query).bind(...params).all();
      return json(results);
    }

    if (path === "/sync/status" && method === "GET") {
      const { results } = await env.DB.prepare(
        `SELECT source, site, last_synced_at, last_date_covered, row_count, status
         FROM sync_log
         WHERE id IN (
           SELECT MAX(id) FROM sync_log GROUP BY source, site
         )
         ORDER BY last_synced_at DESC`
      ).all();
      return json(results);
    }

    
    // === 기간별 수익 분석 엔드포인트 ===
    if (path === "/analysis/period-report" && method === "GET") {
      const days = parseInt(url.searchParams.get("days") || "1");
      const limit = parseInt(url.searchParams.get("limit") || "20");

      // 기간 계산
      const now = new Date();
      const start = new Date(now);
      start.setDate(start.getDate() - days);
      const startStr = start.toISOString().slice(0, 10);

      // 사이트별 요약
      const { results: siteSummary } = await env.DB.prepare(
        `SELECT site,
                SUM(pageviews) as total_pv,
                SUM(revenue) as total_rev,
                COUNT(DISTINCT page) as pages,
                COUNT(DISTINCT date) as days_active
         FROM ga4_pageviews
         WHERE date >= ?
         GROUP BY site
         ORDER BY total_rev DESC`
      ).bind(startStr).all();

      // 페이지별 상위 수익 (RPM 포함)
      const { results: topPages } = await env.DB.prepare(
        `SELECT site, page,
                SUM(pageviews) as pv,
                SUM(revenue) as rev,
                ROUND(CASE WHEN SUM(pageviews) > 0 THEN SUM(revenue) * 1000.0 / SUM(pageviews) ELSE 0 END, 2) as rpm
         FROM ga4_pageviews
         WHERE date >= ? AND pageviews > 0
         GROUP BY site, page
         HAVING SUM(revenue) > 0
         ORDER BY rev DESC
         LIMIT ?`
      ).bind(startStr, limit).all();

      // 페이지별 상위 PV (수익 0 포함)
      const { results: topPvPages } = await env.DB.prepare(
        `SELECT site, page,
                SUM(pageviews) as pv,
                SUM(revenue) as rev,
                ROUND(CASE WHEN SUM(pageviews) > 0 THEN SUM(revenue) * 1000.0 / SUM(pageviews) ELSE 0 END, 2) as rpm
         FROM ga4_pageviews
         WHERE date >= ? AND pageviews > 0
         GROUP BY site, page
         ORDER BY pv DESC
         LIMIT ?`
      ).bind(startStr, limit).all();

      // 고RPM 페이지 (최소 PV 기준)
      const minPv = days <= 1 ? 3 : days <= 3 ? 5 : days <= 7 ? 10 : 30;
      const { results: highRpm } = await env.DB.prepare(
        `SELECT site, page,
                SUM(pageviews) as pv,
                SUM(revenue) as rev,
                ROUND(CASE WHEN SUM(pageviews) > 0 THEN SUM(revenue) * 1000.0 / SUM(pageviews) ELSE 0 END, 2) as rpm
         FROM ga4_pageviews
         WHERE date >= ? AND pageviews > 0
         GROUP BY site, page
         HAVING SUM(pageviews) >= ? AND SUM(revenue) > 0
         ORDER BY rpm DESC
         LIMIT ?`
      ).bind(startStr, minPv, limit).all();

      // 전체 합산
      const totals = siteSummary.reduce((acc, s) => {
        acc.pv += (s.total_pv || 0);
        acc.rev += (s.total_rev || 0);
        return acc;
      }, { pv: 0, rev: 0 });

      return json({
        period: { days, start: startStr, end: now.toISOString().slice(0, 10) },
        totals: {
          pv: totals.pv,
          revenue: Math.round(totals.rev * 100) / 100,
          rpm: totals.pv > 0 ? Math.round(totals.rev / totals.pv * 1000 * 100) / 100 : 0,
          sites: siteSummary.length
        },
        site_summary: siteSummary,
        top_revenue_pages: topPages,
        top_pv_pages: topPvPages,
        high_rpm_pages: highRpm
      });
    }

    
    // === Bing 전용 엔드포인트 ===
    if (path === "/bing/daily" && method === "POST") {
      const body = await request.json();
      const rows = body.rows || [body];
      let count = 0;
      for (const r of rows) {
        await env.DB.prepare(
          "INSERT OR REPLACE INTO bing_daily (site, date, clicks, impressions, account) VALUES (?, ?, ?, ?, ?)"
        ).bind(r.site, r.date, r.clicks || 0, r.impressions || 0, r.account || null).run();
        count++;
      }
      return json({ ok: true, count });
    }

    if (path === "/bing/daily" && method === "GET") {
      const site = url.searchParams.get("site");
      const days = parseInt(url.searchParams.get("days") || "30");
      const start = new Date();
      start.setDate(start.getDate() - days);
      const startStr = start.toISOString().slice(0, 10);
      let query = "SELECT * FROM bing_daily WHERE date >= ?";
      const params = [startStr];
      if (site) { query += " AND site = ?"; params.push(site); }
      query += " ORDER BY date DESC, site";
      const { results } = await env.DB.prepare(query).bind(...params).all();
      return json(results);
    }

    if (path === "/bing/keywords" && method === "POST") {
      const body = await request.json();
      const rows = body.keywords || [body];
      let count = 0;
      for (const r of rows) {
        await env.DB.prepare(
          "INSERT OR REPLACE INTO bing_keywords (site, date, query, clicks, impressions, ctr, position, account) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        ).bind(r.site, r.date, r.query, r.clicks || 0, r.impressions || 0, r.ctr || 0, r.position || 0, r.account || null).run();
        count++;
      }
      return json({ ok: true, count });
    }

    if (path === "/bing/keywords" && method === "GET") {
      const site = url.searchParams.get("site");
      const days = parseInt(url.searchParams.get("days") || "30");
      const limit = parseInt(url.searchParams.get("limit") || "100");
      const start = new Date();
      start.setDate(start.getDate() - days);
      const startStr = start.toISOString().slice(0, 10);
      let query = "SELECT site, query, SUM(clicks) as clicks, SUM(impressions) as impressions, ROUND(AVG(position),1) as position FROM bing_keywords WHERE date >= ?";
      const params = [startStr];
      if (site) { query += " AND site = ?"; params.push(site); }
      query += " GROUP BY site, query ORDER BY impressions DESC LIMIT ?";
      params.push(limit);
      const { results } = await env.DB.prepare(query).bind(...params).all();
      return json(results);
    }

    if (path === "/bing/summary" && method === "GET") {
      const days = parseInt(url.searchParams.get("days") || "30");
      const start = new Date();
      start.setDate(start.getDate() - days);
      const startStr = start.toISOString().slice(0, 10);
      const { results: daily } = await env.DB.prepare(
        "SELECT site, SUM(clicks) as clicks, SUM(impressions) as impressions FROM bing_daily WHERE date >= ? GROUP BY site ORDER BY impressions DESC"
      ).bind(startStr).all();
      const { results: kwCount } = await env.DB.prepare(
        "SELECT COUNT(DISTINCT query) as cnt FROM bing_keywords WHERE date >= ?"
      ).bind(startStr).all();
      return json({ sites: daily, unique_keywords: kwCount[0]?.cnt || 0 });
    }


    // === 사이트 노출 추적 ===
    if (path === "/exposure/init" && method === "POST") {
      await env.DB.prepare("CREATE TABLE IF NOT EXISTS site_exposure (id INTEGER PRIMARY KEY AUTOINCREMENT, site TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'unknown', first_impression_date TEXT, first_click_date TEXT, registered_date TEXT, latest_impressions INTEGER DEFAULT 0, latest_clicks INTEGER DEFAULT 0, week1_impressions INTEGER DEFAULT 0, week2_impressions INTEGER DEFAULT 0, week3_impressions INTEGER DEFAULT 0, week4_impressions INTEGER DEFAULT 0, status TEXT DEFAULT 'waiting', updated_at TEXT, UNIQUE(site, source))").run();
      return json({ ok: true, message: "site_exposure table ready" });
    }

    if (path === "/exposure/update" && method === "POST") {
      const body = await request.json();
      const rows = body.data || [];
      let updated = 0;
      for (const r of rows) {
        await env.DB.prepare(`
          INSERT INTO site_exposure (site, source, first_impression_date, first_click_date, latest_impressions, latest_clicks, status, updated_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
          ON CONFLICT(site, source) DO UPDATE SET
            first_impression_date = COALESCE(site_exposure.first_impression_date, excluded.first_impression_date),
            first_click_date = COALESCE(site_exposure.first_click_date, excluded.first_click_date),
            latest_impressions = excluded.latest_impressions,
            latest_clicks = excluded.latest_clicks,
            status = excluded.status,
            updated_at = datetime('now')
        `).bind(
          r.site, r.source,
          r.first_impression_date || null,
          r.first_click_date || null,
          r.latest_impressions || 0,
          r.latest_clicks || 0,
          r.status || 'waiting'
        ).run();
        updated++;
      }
      return json({ ok: true, updated });
    }

    if (path === "/exposure/weekly" && method === "POST") {
      const body = await request.json();
      const week = body.week || 1;
      const rows = body.data || [];
      const col = "week" + week + "_impressions";
      if (![1,2,3,4].includes(week)) return json({ error: "week must be 1-4" }, 400);
      let updated = 0;
      for (const r of rows) {
        await env.DB.prepare(
          `UPDATE site_exposure SET ${col} = ?, updated_at = datetime('now') WHERE site = ? AND source = ?`
        ).bind(r.impressions || 0, r.site, r.source).run();
        updated++;
      }
      return json({ ok: true, updated });
    }

    if (path === "/exposure/status" && method === "GET") {
      const { results } = await env.DB.prepare(
        `SELECT * FROM site_exposure ORDER BY 
         CASE status WHEN 'growing' THEN 1 WHEN 'exposed' THEN 2 WHEN 'waiting' THEN 3 ELSE 4 END,
         latest_impressions DESC`
      ).all();
      const waiting = results.filter(r => r.status === 'waiting').length;
      const exposed = results.filter(r => r.status === 'exposed').length;
      const growing = results.filter(r => r.status === 'growing').length;
      return json({ total: results.length, waiting, exposed, growing, sites: results });
    }

    if (path === "/exposure/new" && method === "GET") {
      const days = url.searchParams.get("days") || "7";
      const { results } = await env.DB.prepare(
        `SELECT * FROM site_exposure 
         WHERE first_impression_date >= date('now', '-' || ? || ' days')
         ORDER BY first_impression_date DESC`
      ).bind(days).all();
      return json(results);
    }

    // === 사이트별 상위 페이지 ===
    if (path === "/analysis/site-pages" && method === "GET") {
      const site = url.searchParams.get("site");
      const days = parseInt(url.searchParams.get("days") || "30");
      const limit = parseInt(url.searchParams.get("limit") || "30");
      if (!site) return json({ error: "site parameter required" }, 400);
      const start = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
      try {
        const { results } = await env.DB.prepare(
          `SELECT page, SUM(pageviews) as pv, SUM(sessions) as sessions, SUM(revenue) as revenue,
           CASE WHEN SUM(pageviews) > 0 THEN ROUND(SUM(revenue) / SUM(pageviews) * 1000, 2) ELSE 0 END as rpm
           FROM ga4_pageviews WHERE site = ? AND date >= ? GROUP BY page ORDER BY pv DESC LIMIT ?`
        ).bind(site, start, limit).all();
        const total_pv = results.reduce((a, r) => a + (r.pv || 0), 0);
        const total_rev = results.reduce((a, r) => a + (r.revenue || 0), 0);
        return json({ site, days, total_pv, total_revenue: Math.round(total_rev * 100) / 100, pages: results });
      } catch (e) {
        return json({ error: e.message }, 500);
      }
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

