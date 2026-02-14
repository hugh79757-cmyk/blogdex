"""sync 공통 유틸리티 - 중복 방지 및 배치 저장"""
from api import get, post
from rich.console import Console

console = Console()


def get_existing_posts(blog_id):
    """DB에 저장된 해당 블로그의 포스트 제목 set 반환"""
    results = get("/posts/search", params={"q": "", "blog_id": blog_id})
    if isinstance(results, dict):
        results = results.get("results", [])
    existing = set()
    for p in results:
        if str(p.get("blog_id")) == str(blog_id):
            title = p.get("title", "")
            if isinstance(title, list):
                title = title[0] if title else ""
            existing.add(str(title).strip().lower())
    return existing


def safe_title(title):
    """title이 list, None 등일 때 안전하게 문자열로 변환"""
    if title is None:
        return ""
    if isinstance(title, list):
        return title[0] if title else ""
    return str(title)


def save_new_posts(all_posts, existing_titles, blog_name):
    """기존에 없는 포스트만 필터링 후 배치 저장"""
    new_posts = []
    skipped = 0
    for p in all_posts:
        title = safe_title(p.get("title", ""))
        p["title"] = title
        if title.strip().lower() in existing_titles:
            skipped += 1
        else:
            new_posts.append(p)

    if new_posts:
        for i in range(0, len(new_posts), 100):
            batch = new_posts[i:i + 100]
            post("/posts", {"posts": batch})
        console.print(f"  [green]{blog_name}: 신규 {len(new_posts)}개 저장 (기존 {skipped}개 스킵)[/]")
    else:
        console.print(f"  [yellow]{blog_name}: 신규 글 없음 (기존 {skipped}개 모두 존재)[/]")

    return len(new_posts), skipped
