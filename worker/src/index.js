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

      // --- 타이틀 필터 조회 (status별) ---
      if (path === "/titles/filter" && method === "GET") {
        const status = url.searchParams.get("status") || "all";
        const page = parseInt(url.searchParams.get("page") || "1");
        const limit = parseInt(url.searchParams.get("limit") || "50");
        const offset = (page - 1) * limit;
        let rows, countRow;
        if (status === "all") {
          countRow = await env.DB.prepare("SELECT COUNT(*) as total FROM collected_titles").first();
          const { results } = await env.DB.prepare("SELECT * FROM collected_titles ORDER BY id DESC LIMIT ? OFFSET ?").bind(limit, offset).all();
          rows = results;
        } else {
          countRow = await env.DB.prepare("SELECT COUNT(*) as total FROM collected_titles WHERE status = ?").bind(status).first();
          const { results } = await env.DB.prepare("SELECT * FROM collected_titles WHERE status = ? ORDER BY id DESC LIMIT ? OFFSET ?").bind(status, limit, offset).all();
          rows = results;
        }
        return json({ total: countRow?.total || 0, page, limit, data: rows });
      }

      // --- 타이틀 상세 (클릭시 정보) ---
      if (path.startsWith("/titles/detail/") && method === "GET") {
        const titleId = path.split("/titles/detail/")[1];
        const { results: titleRows } = await env.DB.prepare("SELECT * FROM collected_titles WHERE id = ?").bind(titleId).all();
        if (titleRows.length === 0) return json({ error: "Not found" }, 404);
        const title = titleRows[0];
        const stopWords = ['the','a','an','is','are','was','were','be','been','being','have','has','had','do','does','did','will','would','shall','should','may','might','must','can','could','이','그','저','것','수','등','및','또','더','를','을','에','의','가','은','는','으로','에서','와','과','도','만','부터','까지','처럼','같은','한국','한국은','처음','처음이지','어서','어서와','텐트','밖은','유럽','맛집','레시피','만들기','방송','특집','편','일','월','년','집','곳','때','중','후','전','것','들','위','속','간'];
        const words = title.title.split(/\s+/).filter(w => w.length >= 2 && !stopWords.includes(w.toLowerCase())).slice(0, 6);
        
        // 관련 포스트 - 최소 2개 키워드 동시 매칭
        let relatedPosts = [];
        if (words.length >= 2) {
          const { results: allPosts } = await env.DB.prepare("SELECT p.*, b.name as blog_name FROM my_posts p JOIN blogs b ON p.blog_id = b.id").all();
          for (const p of allPosts) {
            if (!p.title) continue;
            const matchCount = words.filter(w => p.title.includes(w)).length;
            if (matchCount >= 2) {
              relatedPosts.push({ ...p, match_count: matchCount });
            }
          }
          relatedPosts.sort((a, b) => b.match_count - a.match_count);
          relatedPosts = relatedPosts.slice(0, 10);
        }
        
        // GSC 키워드 - 핵심 키워드 2개 이상 포함된 것만
        let gscData = [];
        if (words.length >= 2) {
          const topWords = words.slice(0, 4);
          const { results: allKw } = await env.DB.prepare("SELECT site, query, SUM(clicks) as clicks, SUM(impressions) as impressions, AVG(position) as avg_position FROM gsc_keywords GROUP BY site, query HAVING impressions >= 1 ORDER BY impressions DESC").all();
          for (const kw of allKw) {
            const matchCount = topWords.filter(w => kw.query.includes(w)).length;
            if (matchCount >= 2) {
              gscData.push({ ...kw, match_count: matchCount });
            }
          }
          gscData.sort((a, b) => b.match_count - a.match_count || b.impressions - a.impressions);
          gscData = gscData.slice(0, 20);
        }
        
        return json({ title: title, related_posts: relatedPosts, gsc_keywords: gscData });
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

