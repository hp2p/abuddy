"""
anthropic.skilljar.com 강좌 페이지 크롤러

사용법:
  uv run scripts/download_skilljar.py

실행하면 브라우저 창이 열립니다.
  1. anthropic.skilljar.com 에 직접 로그인
  2. 로그인 완료 후 터미널에서 Enter 입력
  3. 홈페이지부터 강좌→레슨 순으로 자동 크롤링·저장

다운로드 결과: CCA/skilljar/ 디렉토리에 강좌별 폴더로 저장
"""

import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import Page, async_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "CCA" / "skilljar"
BASE = "https://anthropic.skilljar.com"

visited: set[str] = set()


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def normalize(url: str) -> str:
    p = urlparse(url)
    return p._replace(fragment="", query="").geturl().rstrip("/")


def same_domain(url: str) -> bool:
    return urlparse(url).netloc == urlparse(BASE).netloc


def is_asset(url: str) -> bool:
    return bool(re.search(r"\.(png|jpg|jpeg|gif|svg|ico|css|js|woff|mp4|webm|pdf)(\?|$)", url, re.I))


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/").replace("/", "_")
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", path)[:120] or "index"


def html_to_markdown(html: str, url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "nav", "footer", "iframe",
                               "aside", "noscript", "svg"]):
        tag.decompose()

    main = (
        soup.find("main") or
        soup.find("article") or
        soup.find(id=re.compile(r"content|main|lesson|course", re.I)) or
        soup.find(class_=re.compile(r"content|lesson|course|body|training|curriculum", re.I)) or
        soup.find("body")
    )

    lines = [f"<!-- source: {url} -->\n"]
    title_el = soup.find("title")
    if title_el:
        lines.append(f"# {title_el.get_text(strip=True)}\n")

    if main:
        for el in main.find_all(
            ["h1","h2","h3","h4","h5","p","li","pre","code","blockquote","td","th"],
            recursive=True,
        ):
            text = el.get_text(separator=" ", strip=True)
            if not text or len(text) < 2:
                continue
            tag = el.name
            if tag == "h1":            lines.append(f"\n# {text}")
            elif tag == "h2":          lines.append(f"\n## {text}")
            elif tag == "h3":          lines.append(f"\n### {text}")
            elif tag in ("h4","h5"):   lines.append(f"\n#### {text}")
            elif tag == "li":          lines.append(f"- {text}")
            elif tag in ("pre","code"):lines.append(f"\n```\n{text}\n```")
            elif tag == "blockquote":  lines.append(f"\n> {text}")
            elif tag in ("td","th"):   lines.append(f"| {text} |")
            else:                      lines.append(f"\n{text}")

    return "\n".join(lines)


def extract_links(html: str, current_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        full = normalize(urljoin(current_url, href))
        if same_domain(full) and not is_asset(full):
            links.append(full)
    return links


# ── 핵심: 접힌 요소 모두 펼치기 ──────────────────────────────────────────────

async def expand_all(page: Page):
    """
    페이지 내 접힌 아코디언·토글·details 요소를 모두 펼친다.
    여러 패턴을 순서대로 시도.
    """

    # 1) HTML <details> 태그 (열리지 않은 것)
    await page.evaluate("""
        document.querySelectorAll('details:not([open])').forEach(el => {
            el.setAttribute('open', '');
        });
    """)

    # 2) aria-expanded="false" 인 버튼/div 클릭
    collapsed = await page.query_selector_all('[aria-expanded="false"]')
    if collapsed:
        logger.info(f"    aria-expanded=false 요소 {len(collapsed)}개 클릭 중...")
    for el in collapsed:
        try:
            await el.scroll_into_view_if_needed()
            await el.click(timeout=3_000)
            await asyncio.sleep(0.2)
        except Exception:
            pass

    # 3) 일반적인 아코디언 헤더 클릭 (Skilljar 특유 클래스 패턴)
    accordion_selectors = [
        ".accordion-header:not(.expanded)",
        ".accordion-toggle",
        ".section-header.collapsed",
        ".curriculum-item-toggle",
        ".lesson-section-toggle",
        "[data-toggle='collapse'][aria-expanded='false']",
        ".collapse-toggle:not(.open)",
        ".sj-toggle:not(.open)",           # Skilljar 전용
        ".sj-curriculum-section-toggle",   # Skilljar 전용
        "summary",                          # <details><summary> 패턴
    ]
    for sel in accordion_selectors:
        els = await page.query_selector_all(sel)
        if not els:
            continue
        logger.info(f"    {sel} 요소 {len(els)}개 클릭 중...")
        for el in els:
            try:
                if not await el.is_visible():
                    continue
                await el.scroll_into_view_if_needed()
                await el.click(timeout=3_000)
                await asyncio.sleep(0.15)
            except Exception:
                pass

    # 4) 클릭 후 새로 생긴 aria-expanded=false 요소 재처리 (중첩 아코디언)
    collapsed2 = await page.query_selector_all('[aria-expanded="false"]')
    for el in collapsed2:
        try:
            if await el.is_visible():
                await el.scroll_into_view_if_needed()
                await el.click(timeout=3_000)
                await asyncio.sleep(0.15)
        except Exception:
            pass

    # DOM 안정화 대기
    await asyncio.sleep(0.5)


# ── 페이지 저장 ───────────────────────────────────────────────────────────────

async def visit_and_save(page: Page, url: str, dest: Path) -> list[str]:
    """url 방문 → 확장 → 저장 → 내부 링크 반환"""
    if url in visited:
        return []
    visited.add(url)

    logger.info(f"  ↳ {url}")
    try:
        await page.goto(url, wait_until="networkidle", timeout=30_000)
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.warning(f"    로드 실패: {e}")
        return []

    # 접힌 요소 펼치기
    await expand_all(page)

    html = await page.content()
    md = html_to_markdown(html, url)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(md, encoding="utf-8")
    logger.success(f"    저장: {dest.relative_to(OUTPUT_DIR.parent.parent)} ({len(md):,} chars)")

    return extract_links(html, url)


# ── 강좌 크롤링 ───────────────────────────────────────────────────────────────

def is_lesson_link(url: str, course_path: str) -> bool:
    p = urlparse(url).path
    return (
        p.startswith(course_path + "/") or
        "/page/" in p or
        "/lesson/" in p or
        "/series/" in p
    )


async def crawl_course(page: Page, course_url: str, course_slug: str):
    course_dir = OUTPUT_DIR / course_slug
    course_path = urlparse(course_url).path.rstrip("/")

    logger.info(f"\n📚 강좌 시작: {course_slug}")

    # 강좌 인덱스 저장
    links = await visit_and_save(page, course_url, course_dir / "index.md")

    # 레슨 링크 추출 (강좌 하위 경로만)
    lesson_urls = list(dict.fromkeys(
        l for l in links
        if is_lesson_link(l, course_path) and l != course_url and l not in visited
    ))
    logger.info(f"  레슨 링크 {len(lesson_urls)}개 발견")

    for lesson_url in lesson_urls:
        fname = slug_from_url(lesson_url) + ".md"
        sub_links = await visit_and_save(page, lesson_url, course_dir / fname)

        # 레슨 내 하위 페이지도 처리 (예: 멀티파트 레슨)
        sub_lessons = [
            l for l in sub_links
            if is_lesson_link(l, course_path) and l not in visited
        ]
        for sub_url in sub_lessons:
            sub_fname = slug_from_url(sub_url) + ".md"
            await visit_and_save(page, sub_url, course_dir / sub_fname)
            await asyncio.sleep(0.2)

        await asyncio.sleep(0.3)


# ── 홈 크롤링 ────────────────────────────────────────────────────────────────

async def crawl_home(page: Page) -> list[tuple[str, str]]:
    logger.info(f"\n🏠 홈페이지 크롤링: {BASE}")
    visited.add(normalize(BASE))

    await page.goto(BASE, wait_until="networkidle", timeout=30_000)
    await asyncio.sleep(0.5)
    await expand_all(page)  # 홈페이지도 펼치기

    html = await page.content()
    (OUTPUT_DIR / "_home.md").write_text(html_to_markdown(html, BASE), encoding="utf-8")
    logger.success(f"  홈 저장: _home.md")

    all_links = extract_links(html, BASE)

    # 비-강좌 경로 제외 목록
    SKIP_PATHS = {
        "sign-in", "sign-up", "logout", "dashboard", "catalog", "search",
        "forgot-password", "help", "privacy", "terms", "contact", "about",
        "reset-password", "profile", "account", "notifications",
    }
    SKIP_PREFIXES = ("/auth/", "/api/", "/cdn/", "/static/", "/assets/")

    course_links: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    for url in all_links:
        if url in seen_urls:
            continue
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # 비-강좌 패턴 제외
        if not path:
            continue
        if any(path == s or path.startswith(s + "/") for s in SKIP_PATHS):
            continue
        if any(parsed.path.startswith(p) for p in SKIP_PREFIXES):
            continue

        seen_urls.add(url)
        # slug: 경로의 첫 번째 세그먼트를 폴더명으로
        slug = path.split("/")[0]
        slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", slug)[:80]
        course_links.append((slug, url))

    # slug 중복 제거 (같은 slug면 첫 번째만)
    seen_slugs: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for slug, url in course_links:
        if slug not in seen_slugs:
            seen_slugs.add(slug)
            deduped.append((slug, url))

    logger.info(f"  강좌 후보 {len(deduped)}개: {[s for s,_ in deduped]}")
    return deduped


# ── 메인 ─────────────────────────────────────────────────────────────────────

async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, format="{time:HH:mm:ss} | {level:<7} | {message}", level="INFO")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=20)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        # 로그인 대기
        await page.goto(BASE, wait_until="domcontentloaded")
        print("\n" + "="*60)
        print("  브라우저에서 로그인을 완료해 주세요.")
        print("  완료 후 여기서 Enter ↵")
        print("="*60 + "\n")
        input()

        # 홈에서 강좌 목록 수집
        course_list = await crawl_home(page)

        if not course_list:
            logger.warning("강좌 링크를 찾지 못했습니다.")
            logger.info(f"_home.md 를 확인해서 구조를 파악해주세요: {OUTPUT_DIR / '_home.md'}")
        else:
            for slug, url in course_list:
                await crawl_course(page, url, slug)
                await asyncio.sleep(1)

        await browser.close()

    total = len(list(OUTPUT_DIR.rglob("*.md")))
    print(f"\n✓ 완료! 총 {total}개 파일 → {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
