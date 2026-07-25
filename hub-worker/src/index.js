const DOMAIN_SITES = {
  "rotcha.kr": [
    "rotcha.kr", "hotissue.rotcha.kr", "travel.rotcha.kr",
    "tour1.rotcha.kr", "travel1.rotcha.kr", "travel2.rotcha.kr",
    "tour2.rotcha.kr", "tour3.rotcha.kr", "tco.rotcha.kr",
    "deal.rotcha.kr", "compare.rotcha.kr", "guide.rotcha.kr",
    "ev.rotcha.kr", "sports.rotcha.kr",     "kbo.rotcha.kr",
  ],
  "techpawz.com": [
    "techpawz.com", "2.techpawz.com",
    "adventure.techpawz.com", "airlines.techpawz.com",
    "airports.techpawz.com", "biz.techpawz.com",
    "bus.techpawz.com", "cruise.techpawz.com",
    "culture.techpawz.com", "daytrips.techpawz.com",
    "deals.techpawz.com", "dining.techpawz.com",
    "dividend.techpawz.com", "esim.techpawz.com",
    "etf.techpawz.com", "eurail.techpawz.com",
    "ferry.techpawz.com", "finance.techpawz.com",
    "flights.techpawz.com", "foodtour.techpawz.com",
    "info.techpawz.com", "ipo.techpawz.com",
    "issue.techpawz.com", "michelin.techpawz.com",
    "multiday.techpawz.com", "nature.techpawz.com",
    "phototour.techpawz.com", "sector.techpawz.com",
    "tour.techpawz.com", "tours.techpawz.com",
    "trains.techpawz.com", "transfers.techpawz.com",
    "visa.techpawz.com", "visafree.techpawz.com",
    "walking.techpawz.com", "watersports.techpawz.com",
    "zodiac.techpawz.com",
  ],
  "informationhot.kr": [
    "informationhot.kr", "5.informationhot.kr", "6.informationhot.kr",
    "65.informationhot.kr", "7.informationhot.kr", "8.informationhot.kr",
    "appliance.informationhot.kr", "apply.informationhot.kr",
    "apt.informationhot.kr", "baby.informationhot.kr",
    "beauty.informationhot.kr", "betguide.informationhot.kr",
    "brand.informationhot.kr", "camping.informationhot.kr",
    "fitness.informationhot.kr", "fsched.informationhot.kr",
    "fstats.informationhot.kr", "health.informationhot.kr",
    "interior.informationhot.kr", "kboplayer.informationhot.kr",
    "kboschedule.informationhot.kr", "kboteam.informationhot.kr",
    "kitchen.informationhot.kr", "kuta.informationhot.kr",
    "laptop.informationhot.kr", "pet.informationhot.kr",
    "pick.informationhot.kr", "proto.informationhot.kr",
    "protoking.informationhot.kr", "protostats.informationhot.kr",
    "rank.informationhot.kr", "rent.informationhot.kr",
    "senior.informationhot.kr", "simprotection.informationhot.kr",
    "stock.informationhot.kr", "tax.informationhot.kr",
    "tv-show.informationhot.kr", "ud.informationhot.kr",
  ],
  "aikorea24.kr": [
    "aikorea24.kr", "cert.aikorea24.kr",
    "heritage.aikorea24.kr", "keyword.aikorea24.kr",
    "persona.aikorea24.kr",
  ],
};

function getRootDomain(hostname) {
  for (const domain of Object.keys(DOMAIN_SITES)) {
    if (hostname === domain || hostname.endsWith("." + domain)) {
      return domain;
    }
  }
  return null;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const hostname = url.hostname;
    const rootDomain = getRootDomain(hostname);

    // robots.txt
    if (url.pathname === "/robots.txt") {
      const robotsTxt = `User-agent: *
Allow: /sites
Sitemap: https://${hostname}/sitemap.xml`;
      return new Response(robotsTxt, { headers: { "Content-Type": "text/plain" } });
    }

    // sitemap.xml
    if (url.pathname === "/sitemap.xml" && rootDomain) {
      const sites = DOMAIN_SITES[rootDomain] || [];
      const urls = sites.map(s => `<url><loc>https://${s}/</loc></url>`).join("\n");
      const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://${hostname}/sites</loc></url>
${urls}
</urlset>`;
      return new Response(xml, { headers: { "Content-Type": "application/xml" } });
    }

    if (!rootDomain) {
      return new Response("Not found", { status: 404 });
    }

    const sites = DOMAIN_SITES[rootDomain] || [];

    // D1에서 각 서브도메인의 최신 글 조회
    const siteData = [];
    for (const site of sites) {
      const posts = await env.DB.prepare(
        `SELECT p.title, p.url, p.published_at, b.name as blog_name
         FROM my_posts p
         JOIN blogs b ON p.blog_id = b.id
         WHERE p.url LIKE ?
         ORDER BY p.published_at DESC
         LIMIT 5`
      ).bind(`%${site}%`).all();

      siteData.push({
        domain: site,
        url: `https://${site}/`,
        posts: posts.results || [],
      });
    }

    const html = generateHTML(rootDomain, siteData);
    return new Response(html, {
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  },
};

function generateHTML(rootDomain, siteData) {
  const now = new Date().toISOString().slice(0, 10);

  const siteBlocks = siteData.map((site) => {
    const postList = site.posts.length > 0
      ? site.posts.map((p) => {
          const date = p.published_at ? p.published_at.slice(0, 10) : "";
          return `<li><a href="${escapeHtml(p.url)}">${escapeHtml(p.title)}</a> <small>${date}</small></li>`;
        }).join("\n")
      : "<li>등록된 글 없음</li>";

    return `
    <div class="site-card">
      <h2><a href="${escapeHtml(site.url)}">${escapeHtml(site.domain)}</a></h2>
      <ul>${postList}</ul>
    </div>`;
  }).join("\n");

  return `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(rootDomain)} - 사이트 네트워크</title>
  <meta name="description" content="${escapeHtml(rootDomain)} 네트워크의 모든 사이트와 최신 글 목록입니다.">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8f9fa; color: #333; line-height: 1.6; padding: 2rem; max-width: 1200px; margin: 0 auto; }
    h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
    .updated { color: #888; font-size: 0.85rem; margin-bottom: 2rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 1.5rem; }
    .site-card { background: #fff; border-radius: 12px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    .site-card h2 { font-size: 1.1rem; margin-bottom: 0.8rem; }
    .site-card h2 a { color: #1a73e8; text-decoration: none; }
    .site-card h2 a:hover { text-decoration: underline; }
    .site-card ul { list-style: none; }
    .site-card li { padding: 0.3rem 0; border-bottom: 1px solid #f0f0f0; font-size: 0.9rem; }
    .site-card li:last-child { border-bottom: none; }
    .site-card li a { color: #333; text-decoration: none; }
    .site-card li a:hover { color: #1a73e8; }
    .site-card li small { color: #999; }
  </style>
</head>
<body>
  <h1>${escapeHtml(rootDomain)} 네트워크</h1>
  <p class="updated">${siteData.length}개 사이트 | 업데이트: ${now}</p>
  <div class="grid">
    ${siteBlocks}
  </div>
</body>
</html>`;
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
