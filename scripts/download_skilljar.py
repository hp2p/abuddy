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

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import BrowserContext, Page, async_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "CCA" / "skilljar"
BASE = "https://anthropic.skilljar.com"
SESSION_FILE = Path(__file__).parent / ".skilljar_session.json"

ATTACHMENT_EXTS = re.compile(r"\.(pdf|zip|docx|pptx|xlsx|doc|ppt|xls|csv)(\?|$)", re.I)
VIDEO_PROCESSING_MSG = "this video is still being processed"

visited: set[str] = set()


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def normalize(url: str) -> str:
    p = urlparse(url)
    return p._replace(fragment="", query="").geturl().rstrip("/")


def same_domain(url: str) -> bool:
    return urlparse(url).netloc == urlparse(BASE).netloc


def is_nav_asset(url: str) -> bool:
    """이미지·스타일시트·스크립트 등 탐색 불필요 자산 (첨부파일 제외)"""
    return bool(re.search(r"\.(png|jpg|jpeg|gif|svg|ico|css|js|woff|mp4|webm)(\?|$)", url, re.I))


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
            ["h1","h2","h3","h4","h5","p","li","pre","code","blockquote","td","th","a"],
            recursive=True,
        ):
            text = el.get_text(separator=" ", strip=True)
            if not text or len(text) < 2:
                continue
            tag = el.name
            if tag == "h1":             lines.append(f"\n# {text}")
            elif tag == "h2":           lines.append(f"\n## {text}")
            elif tag == "h3":           lines.append(f"\n### {text}")
            elif tag in ("h4","h5"):    lines.append(f"\n#### {text}")
            elif tag == "li":           lines.append(f"- {text}")
            elif tag in ("pre","code"): lines.append(f"\n```\n{text}\n```")
            elif tag == "blockquote":   lines.append(f"\n> {text}")
            elif tag in ("td","th"):    lines.append(f"| {text} |")
            elif tag == "a":
                href = el.get("href", "")
                if href and not href.startswith(("#", "javascript:")):
                    full = normalize(urljoin(url, href))
                    lines.append(f"\n[{text}]({full})")
            else:
                lines.append(f"\n{text}")

    return "\n".join(lines)


def extract_links(html: str, current_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        full = normalize(urljoin(current_url, href))
        if same_domain(full) and not is_nav_asset(full):
            links.append(full)
    return links


def extract_attachments(html: str, current_url: str) -> list[tuple[str, str]]:
    """PDF/ZIP/DOCX 등 첨부파일 링크 추출 → [(url, filename), ...]"""
    soup = BeautifulSoup(html, "html.parser")
    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        full = urljoin(current_url, href)
        if ATTACHMENT_EXTS.search(full) and full not in seen:
            seen.add(full)
            raw_name = Path(urlparse(full).path).name
            fname = re.sub(r"[^a-zA-Z0-9._\-]", "_", raw_name)[:120] or "attachment"
            results.append((full, fname))
    return results


# ── 첨부파일 다운로드 ──────────────────────────────────────────────────────────

async def download_attachments(
    attachments: list[tuple[str, str]],
    dest_dir: Path,
    context: BrowserContext,
):
    if not attachments:
        return

    raw_cookies = await context.cookies()
    cookies = {c["name"]: c["value"] for c in raw_cookies}

    dest_dir.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(
        cookies=cookies,
        follow_redirects=True,
        timeout=60,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"},
    ) as client:
        for url, fname in attachments:
            dest = dest_dir / fname
            if dest.exists():
                logger.info(f"    첨부파일 스킵 (이미 존재): {fname}")
                continue
            logger.info(f"    첨부파일 다운로드 중: {fname}")
            try:
                r = await client.get(url)
                r.raise_for_status()
                dest.write_bytes(r.content)
                logger.success(f"    첨부파일 저장: {fname} ({len(r.content):,} bytes)")
            except Exception as e:
                logger.warning(f"    첨부파일 실패: {fname}: {e}")


# ── 퀴즈 처리 ─────────────────────────────────────────────────────────────────

async def _click_first_visible(page: Page, selectors: list[str], timeout: int = 800) -> bool:
    """selectors 순서대로 첫 번째 보이는 버튼 클릭. 성공 시 True."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=timeout):
                await loc.click(timeout=3_000)
                return True
        except Exception:
            pass
    return False


def quiz_results_to_markdown(html: str, url: str) -> str:
    """
    퀴즈 결과 HTML → 마크다운.
    div.show-question 구조 파싱:
      - span.correct / span.incorrect → ✓ / ✗
      - fa-check-square-o → ★ (선택한 답)
      - fa-square-o → ○
    """
    soup = BeautifulSoup(html, "html.parser")
    lines = [f"<!-- source: {url} -->\n", "<!-- QUIZ RESULTS -->\n"]

    # 점수 영역
    for cls in ["score", "results-score", "quiz-score"]:
        el = soup.find(class_=lambda c, k=cls: c and k in " ".join(c).lower())
        if el:
            score_text = el.get_text(separator=" ", strip=True)
            lines.append(f"## 점수\n\n{score_text}\n")
            break

    # 개별 문제 파싱 (Show Answers 클릭 후 나타나는 구조)
    questions = soup.find_all("div", class_="show-question")
    if not questions:
        # Show Answers 이전 화면 — 기본 마크다운으로 fallback
        return html_to_markdown(html, url)

    for q_div in questions:
        # 문제 번호
        q_num_el = q_div.find("span", class_="sj-text-quiz-question")
        q_num = q_num_el.get_text(strip=True) if q_num_el else "?"

        # 정답 여부
        correct_el = q_div.find("span", class_="correct")
        incorrect_el = q_div.find("span", class_="incorrect")
        result = "✓" if correct_el else "✗"

        # 문제 텍스트
        q_text_el = q_div.find("p")
        q_text = q_text_el.get_text(strip=True) if q_text_el else ""

        lines.append(f"\n### {q_num} {result}\n\n{q_text}\n")

        # 선택지 (fa-check-square-o = 선택함, fa-square-o = 미선택)
        for ans_div in q_div.find_all("div", class_="answer"):
            icon_el = ans_div.find("i")
            icon_cls = " ".join(icon_el.get("class", [])) if icon_el else ""
            selected = "fa-check-square-o" in icon_cls
            ans_text_el = ans_div.find("span", class_="answer-text")
            ans_text = ans_text_el.get_text(strip=True) if ans_text_el else ""
            prefix = "★" if selected else "○"
            lines.append(f"- {prefix} {ans_text}")

    return "\n".join(lines)


async def run_quiz(page: Page, url: str) -> str | None:
    """
    퀴즈 페이지 처리.
    Start → (1번 선택 → Next Question) 반복 → Show Answers → 결과 마크다운 반환.
    퀴즈가 아니면 None 반환.
    """
    START_SELS = [
        "button:has-text('Start Quiz')",
        "button:has-text('Start')",
        "a:has-text('Start Quiz')",
        "a:has-text('Begin Quiz')",
        "input[type='submit'][value*='Start']",
    ]
    # Skilljar 퀴즈 Next 버튼: 정확히 "Next Question" 텍스트
    NEXT_SEL = "button:has-text('Next Question')"
    SUBMIT_SELS = [
        "button:has-text('Submit Quiz')",
        "button:has-text('Submit Answers')",
        "button:has-text('Submit')",
        "button:has-text('Finish')",
        "input[type='submit'][value*='Submit']",
    ]
    SHOW_ANSWERS_SELS = [
        "button.sj-text-quiz-show-answers",
        "button:has-text('Show Answers')",
    ]

    # 퀴즈 여부 판단
    has_start = False
    for sel in START_SELS:
        try:
            if await page.locator(sel).first.is_visible(timeout=500):
                has_start = True
                break
        except Exception:
            pass

    radio_count = await page.locator('input[type="radio"]').count()
    checkbox_count = await page.locator('input[type="checkbox"]').count()

    if not has_start and radio_count == 0 and checkbox_count == 0:
        return None  # 퀴즈 아님

    logger.info("    퀴즈 페이지 감지!")

    # Start 클릭
    if has_start:
        if await _click_first_visible(page, START_SELS):
            logger.info("    Start 버튼 클릭 → 대기 중...")
            await asyncio.sleep(2)

    # 문제 순회 (최대 100문제)
    for q_num in range(1, 101):
        r_count = await page.locator('input[type="radio"]').count()
        c_count = await page.locator('input[type="checkbox"]').count()
        total_opts = r_count + c_count

        if total_opts == 0:
            logger.info(f"    선택지 없음 — 결과 페이지로 전환됨")
            break

        logger.info(f"    문제 {q_num} ({total_opts}개 선택지)")

        # 1번 옵션 선택
        try:
            first = (
                page.locator('input[type="radio"]').first
                if r_count > 0
                else page.locator('input[type="checkbox"]').first
            )
            await first.scroll_into_view_if_needed()
            await first.click(timeout=3_000)
            logger.info(f"    문제 {q_num}: 1번 선택 완료")
            await asyncio.sleep(0.8)
        except Exception as e:
            logger.warning(f"    문제 {q_num}: 선택 실패 — {e}")

        # Next Question 클릭 시도
        try:
            next_btn = page.locator(NEXT_SEL).first
            if await next_btn.is_visible(timeout=1_000):
                await next_btn.click(timeout=3_000)
                logger.info(f"    문제 {q_num}: Next Question 클릭")
                await asyncio.sleep(1.5)
                continue
        except Exception:
            pass

        # Next 없으면 Submit/Finish (마지막 문제)
        if await _click_first_visible(page, SUBMIT_SELS, timeout=1_000):
            logger.info(f"    문제 {q_num}: Submit 클릭 — 퀴즈 제출")
            await asyncio.sleep(2)
            break

        logger.info(f"    문제 {q_num}: Next/Submit 버튼 없음 — 퀴즈 종료")
        break

    # 결과 페이지: Show Answers 클릭
    if await _click_first_visible(page, SHOW_ANSWERS_SELS, timeout=3_000):
        logger.info("    Show Answers 클릭 → 정답 표시 대기 중...")
        await asyncio.sleep(1.5)
    else:
        logger.warning("    Show Answers 버튼 없음 — 현재 화면 그대로 저장")

    html = await page.content()
    return quiz_results_to_markdown(html, url)


# ── 핵심: 접힌 요소 모두 펼치기 ──────────────────────────────────────────────

async def expand_all(page: Page):
    """페이지 내 접힌 아코디언·토글·details 요소를 모두 펼친다."""

    # 1) HTML <details> 태그
    await page.evaluate("""
        document.querySelectorAll('details:not([open])').forEach(el => {
            el.setAttribute('open', '');
        });
    """)

    # 2) aria-expanded="false" 인 버튼/div 클릭
    collapsed = await page.query_selector_all('[aria-expanded="false"]')
    if collapsed:
        logger.info(f"    aria-expanded=false 요소 {len(collapsed)}개 클릭 중...")
    for i, el in enumerate(collapsed):
        try:
            if not await el.is_visible():
                logger.debug(f"    [{i+1}/{len(collapsed)}] 비가시 요소 스킵")
                continue
            await el.scroll_into_view_if_needed()
            await el.click(timeout=3_000)
            await asyncio.sleep(0.1)
            logger.info(f"    [{i+1}/{len(collapsed)}] 클릭 완료")
        except Exception as e:
            logger.debug(f"    [{i+1}/{len(collapsed)}] 클릭 실패: {e}")

    # 3) Skilljar 특유 아코디언 패턴
    accordion_selectors = [
        ".accordion-header:not(.expanded)",
        ".accordion-toggle",
        ".section-header.collapsed",
        ".curriculum-item-toggle",
        ".lesson-section-toggle",
        "[data-toggle='collapse'][aria-expanded='false']",
        ".collapse-toggle:not(.open)",
        ".sj-toggle:not(.open)",
        ".sj-curriculum-section-toggle",
        "summary",
    ]
    for sel in accordion_selectors:
        els = await page.query_selector_all(sel)
        if not els:
            continue
        logger.info(f"    {sel} 요소 {len(els)}개 클릭 중...")
        for i, el in enumerate(els):
            try:
                if not await el.is_visible():
                    continue
                await el.scroll_into_view_if_needed()
                await el.click(timeout=3_000)
                await asyncio.sleep(0.1)
                logger.info(f"    [{i+1}/{len(els)}] {sel} 클릭 완료")
            except Exception:
                pass

    # 4) 중첩 아코디언 재처리
    collapsed2 = await page.query_selector_all('[aria-expanded="false"]')
    if collapsed2:
        logger.info(f"    중첩 아코디언 {len(collapsed2)}개 재처리 중...")
    for i, el in enumerate(collapsed2):
        try:
            if await el.is_visible():
                await el.scroll_into_view_if_needed()
                await el.click(timeout=3_000)
                await asyncio.sleep(0.1)
                logger.info(f"    [중첩 {i+1}/{len(collapsed2)}] 클릭 완료")
        except Exception:
            pass

    await asyncio.sleep(0.3)


# ── 페이지 저장 ───────────────────────────────────────────────────────────────

def is_properly_downloaded(dest: Path) -> bool:
    """스킵 여부 판단: VIDEO_ONLY(서버 문제, 재시도 불필요) 또는 실질 텍스트 500자 이상"""
    if not dest.exists():
        return False
    content = dest.read_text(encoding="utf-8")
    if "<!-- VIDEO_ONLY:" in content:
        return True  # 서버쪽 문제, 재시도해도 달라지지 않음
    text_only = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL).strip()
    return len(text_only) > 500


async def visit_and_save(
    page: Page,
    url: str,
    dest: Path,
    context: BrowserContext,
) -> list[str]:
    """url 방문 → 확장 → (퀴즈/일반) 저장 → 첨부파일 다운로드 → 내부 링크 반환"""
    if url in visited:
        return []
    visited.add(url)

    if is_properly_downloaded(dest):
        logger.info(f"  ↳ 스킵 (이미 완료): {dest.name}")
        return []

    logger.info(f"  ↳ {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(3)
    except Exception as e:
        logger.warning(f"    로드 실패: {e}")
        return []

    # 로그아웃 감지: 로그인 페이지로 리다이렉트된 경우
    current_url = page.url
    if "sign-in" in current_url or "login" in current_url or "/auth/" in current_url:
        logger.warning("⚠ 세션 만료 감지 — 브라우저에서 다시 로그인해 주세요.")
        print("\n" + "="*60)
        print("  세션이 만료되었습니다. 브라우저에서 다시 로그인해 주세요.")
        print("  완료 후 여기서 Enter ↵")
        print("="*60 + "\n")
        input()
        # 로그인 후 리다이렉트가 끝날 때까지 대기
        try:
            await page.wait_for_load_state("networkidle", timeout=30_000)
        except Exception:
            pass
        await asyncio.sleep(5)
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(3)

    # 접힌 요소 펼치기
    await expand_all(page)

    html = await page.content()

    # 비디오 처리 중 감지
    if VIDEO_PROCESSING_MSG in html.lower():
        # 실질적인 텍스트 내용이 있는지 확인 (비디오 외)
        md_preview = html_to_markdown(html, url)
        text_only = re.sub(r"<!--.*?-->", "", md_preview, flags=re.DOTALL).strip()
        if len(text_only) < 300:
            logger.warning(f"    비디오 전용 페이지 (처리 중) — 텍스트 없음, 스킵")
            # 최소 정보만 저장
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(f"<!-- source: {url} -->\n\n<!-- VIDEO_ONLY: 비디오 처리 중 -->", encoding="utf-8")
            return extract_links(html, url)
        else:
            logger.warning(f"    비디오 처리 중이나 텍스트 내용 있음 ({len(text_only)}자) — 저장")

    # 퀴즈 처리 (run_quiz가 None 반환 시 일반 페이지)
    quiz_md = await run_quiz(page, url)
    if quiz_md is not None:
        md = quiz_md
        html = await page.content()  # 퀴즈 진행 후 최신 HTML로 링크 추출
    else:
        md = html_to_markdown(html, url)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(md, encoding="utf-8")
    logger.success(f"    저장: {dest.relative_to(OUTPUT_DIR.parent.parent)} ({len(md):,} chars)")

    # 첨부파일 다운로드
    attachments = extract_attachments(html, url)
    if attachments:
        logger.info(f"    첨부파일 {len(attachments)}개 발견: {[f for _, f in attachments]}")
        await download_attachments(attachments, dest.parent, context)

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


async def crawl_course(page: Page, course_url: str, course_slug: str, context: BrowserContext):
    course_dir = OUTPUT_DIR / course_slug
    course_path = urlparse(course_url).path.rstrip("/")

    logger.info(f"\n📚 강좌 시작: {course_slug}")

    links = await visit_and_save(page, course_url, course_dir / "index.md", context)

    lesson_urls = list(dict.fromkeys(
        l for l in links
        if is_lesson_link(l, course_path) and l != course_url and l not in visited
    ))
    logger.info(f"  레슨 링크 {len(lesson_urls)}개 발견")

    for lesson_url in lesson_urls:
        fname = slug_from_url(lesson_url) + ".md"
        sub_links = await visit_and_save(page, lesson_url, course_dir / fname, context)

        sub_lessons = [
            l for l in sub_links
            if is_lesson_link(l, course_path) and l not in visited
        ]
        for sub_url in sub_lessons:
            sub_fname = slug_from_url(sub_url) + ".md"
            await visit_and_save(page, sub_url, course_dir / sub_fname, context)
            await asyncio.sleep(0.2)

        await asyncio.sleep(0.3)


# ── 홈 크롤링 ────────────────────────────────────────────────────────────────

async def crawl_home(page: Page, context: BrowserContext) -> list[tuple[str, str]]:
    logger.info(f"\n🏠 홈페이지 크롤링: {BASE}")
    visited.add(normalize(BASE))

    current = normalize(page.url)
    if current != normalize(BASE):
        try:
            await page.goto(BASE, wait_until="domcontentloaded", timeout=30_000)
        except Exception as e:
            if "interrupted by another navigation" in str(e):
                await page.wait_for_load_state("domcontentloaded", timeout=30_000)
            else:
                raise
    await asyncio.sleep(1)
    await expand_all(page)

    html = await page.content()
    (OUTPUT_DIR / "_home.md").write_text(html_to_markdown(html, BASE), encoding="utf-8")
    logger.success(f"  홈 저장: _home.md")

    all_links = extract_links(html, BASE)

    SKIP_PATHS = {
        "sign-in", "sign-up", "logout", "dashboard", "catalog", "search",
        "forgot-password", "help", "privacy", "terms", "contact", "about",
        "reset-password", "profile", "account", "notifications", "accounts",
    }
    SKIP_PREFIXES = ("/auth/", "/api/", "/cdn/", "/static/", "/assets/")

    course_links: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    for url in all_links:
        if url in seen_urls:
            continue
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path:
            continue
        if any(path == s or path.startswith(s + "/") for s in SKIP_PATHS):
            continue
        if any(parsed.path.startswith(p) for p in SKIP_PREFIXES):
            continue

        seen_urls.add(url)
        slug = path.split("/")[0]
        slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", slug)[:80]
        course_links.append((slug, url))

    seen_slugs: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for slug, url in course_links:
        if slug not in seen_slugs:
            seen_slugs.add(slug)
            deduped.append((slug, url))

    logger.info(f"  강좌 후보 {len(deduped)}개: {[s for s,_ in deduped]}")
    return deduped


# ── 시작 전 실패 파일 정리 ────────────────────────────────────────────────────

def cleanup_failed_files():
    """FETCH ERROR가 포함된 .md 파일 삭제 → 다음 실행 시 재다운로드"""
    deleted = 0
    for md_file in OUTPUT_DIR.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            if "FETCH ERROR" in content or "**FETCH ERROR**" in content:
                md_file.unlink()
                logger.info(f"  실패 파일 삭제: {md_file.relative_to(OUTPUT_DIR)}")
                deleted += 1
        except Exception:
            pass
    if deleted:
        logger.info(f"  총 {deleted}개 실패 파일 삭제 → 재다운로드 예정")


# ── 메인 ─────────────────────────────────────────────────────────────────────

async def main(course: str | None = None):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, format="{time:HH:mm:ss} | {level:<7} | {message}", level="INFO")

    logger.info("실패 파일 정리 중...")
    cleanup_failed_files()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=20)

        # 저장된 세션이 있으면 복원
        if SESSION_FILE.exists():
            logger.info("저장된 세션 복원 중...")
            context = await browser.new_context(
                storage_state=str(SESSION_FILE),
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
        else:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

        page = await context.new_page()
        await page.goto(BASE, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(5)  # JS 리다이렉트 완료 대기

        # 로그인 여부 확인: skilljar 도메인에 머물러 있으면 로그인 상태
        def is_logged_in() -> bool:
            return urlparse(BASE).netloc in page.url

        if not is_logged_in():
            logger.warning(f"로그인 필요 (현재 URL: {page.url})")
            print("\n" + "="*60)
            print("  브라우저에서 로그인을 완료해 주세요.")
            print("  완료 후 여기서 Enter ↵")
            print("="*60 + "\n")
            input()
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=30_000)
            except Exception:
                pass
            await asyncio.sleep(5)  # JS 리다이렉트 완료 대기

        if not is_logged_in():
            logger.error(f"로그인 후에도 skilljar 도메인이 아닙니다: {page.url}")
            logger.error("스크립트를 종료합니다.")
            await browser.close()
            return

        logger.info(f"로그인 확인 완료: {page.url}")

        # 세션 저장
        await context.storage_state(path=str(SESSION_FILE))
        logger.info(f"세션 저장: {SESSION_FILE}")

        if course:
            slug = course.strip("/")
            url = f"{BASE}/{slug}"
            logger.info(f"단일 강좌 모드: {url}")
            course_list = [(slug, url)]
        else:
            course_list = await crawl_home(page, context)

        if not course_list:
            logger.warning("강좌 링크를 찾지 못했습니다.")
            logger.info(f"_home.md 를 확인해주세요: {OUTPUT_DIR / '_home.md'}")
        else:
            for slug, url in course_list:
                await crawl_course(page, url, slug, context)
                await asyncio.sleep(1)

        await browser.close()

    total_md = len(list(OUTPUT_DIR.rglob("*.md")))
    total_attach = len([
        f for f in OUTPUT_DIR.rglob("*")
        if f.suffix.lower() in {".pdf", ".zip", ".docx", ".pptx", ".xlsx"}
    ])
    print(f"\n✓ 완료! MD {total_md}개, 첨부파일 {total_attach}개 → {OUTPUT_DIR}")


import typer

app = typer.Typer()

@app.command()
def cli(
    course: str | None = typer.Option(
        None, "--course", "-c",
        help="특정 강좌 슬러그만 다운로드 (예: building-with-claude-api). 생략 시 전체 크롤링."
    ),
):
    asyncio.run(main(course=course))


if __name__ == "__main__":
    app()
