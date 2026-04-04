#!/usr/bin/env python
"""
CCA/skilljar/ 의 강의 콘텐츠를 concept_id별로 집계하여 S3 docs로 저장.

전략:
  1. Skilljar 코스를 도메인별로 사전 분류 (하드코딩)
  2. 각 concept → 같은 도메인 코스의 레슨을 키워드 매칭으로 선택
  3. Bedrock 요약 생성 → S3 저장 (CCA/docs/{concept_id}.json)

사용법:
  uv run scripts/skilljar_to_docs.py --exam CCA
  uv run scripts/skilljar_to_docs.py --exam CCA --dry-run
  uv run scripts/skilljar_to_docs.py --exam CCA --concept-id d1-agentic-loop
  uv run scripts/skilljar_to_docs.py --exam CCA --force
"""
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import typer
from loguru import logger

sys.path.insert(0, "src")
from abuddy.services.bedrock import summarize_doc_content
from abuddy.services.concept_docs import chunk_pages, doc_exists, save_doc
from abuddy.services.concept_graph import get_all_concepts

SKILLJAR_DIR = Path(__file__).parent.parent / "CCA" / "skilljar"
_BEDROCK_DELAY = 0.5
_MAX_LESSONS_PER_CONCEPT = 4
_MAX_CONTENT_CHARS = 8000

# 도메인 → 관련 Skilljar 코스 슬러그 (관련도 높은 순)
DOMAIN_COURSES: dict[int, list[str]] = {
    # D1: Agentic Architecture & Orchestration
    # claude-code-in-action 포함: task 1.3 hooks(Introducing/Defining/Implementing hooks) 커버
    1: [
        "claude-code-in-action",
        "intro-to-subagents",
        "introduction-to-subagents",
        "building-with-claude-api",
        "claude-with-the-anthropic-api",
        "claude-in-amazon-bedrock",
        "claude-with-google-vertex",
        "claude-101",
        "introduction-to-claude-cowork",
    ],
    # D2: Tool Design & MCP Integration
    # claude-code-in-action 앞으로: Making changes/Adding context 레슨이 built-in tools 커버
    2: [
        "claude-code-in-action",
        "intro-to-mcp",
        "introduction-to-model-context-protocol",
        "model-context-protocol-advanced-topics",
        "mcp-advanced",
        "intro-to-agent-skills",
        "introduction-to-agent-skills",
        "building-with-claude-api",
        "claude-with-the-anthropic-api",
    ],
    # D3: Claude Code Configuration & Workflows
    3: [
        "claude-code-in-action",
        "intro-to-agent-skills",
        "introduction-to-agent-skills",
        "building-with-claude-api",
        "claude-with-the-anthropic-api",
    ],
    # D4: Prompt Engineering & Structured Output
    4: [
        "building-with-claude-api",
        "claude-with-the-anthropic-api",
        "claude-101",
        "ai-capabilities-and-limitations",
        "introduction-to-claude-cowork",
    ],
    # D5: Context Management & Reliability
    5: [
        "building-with-claude-api",
        "claude-with-the-anthropic-api",
        "claude-101",
        "ai-capabilities-and-limitations",
        "introduction-to-claude-cowork",
    ],
}

app = typer.Typer()


# ── Skilljar 파일 로드 ─────────────────────────────────────────

def _extract_source_url(text: str) -> str:
    m = re.search(r"<!--\s*source:\s*(https?://\S+)\s*-->", text)
    return m.group(1) if m else ""


def _extract_title(text: str) -> str:
    m = re.search(r"^#\s+(.+)", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _is_usable(text: str) -> bool:
    """빈 내용이거나 FETCH ERROR인 파일 제외."""
    if "FETCH ERROR" in text:
        return False
    # HTML 주석 제거 후 실질적 내용 확인
    stripped = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()
    return len(stripped) > 200


def load_course_lessons(course_slug: str) -> list[dict]:
    """
    코스 디렉토리에서 레슨 MD 파일을 읽어 [{url, title, content}] 반환.
    index.md, *_resume.md, FETCH ERROR 파일은 제외.
    """
    course_dir = SKILLJAR_DIR / course_slug
    if not course_dir.exists():
        return []

    lessons = []
    for path in sorted(course_dir.glob("*.md")):
        if path.stem == "index" or path.stem.endswith("_resume"):
            continue
        text = path.read_text(encoding="utf-8")
        if not _is_usable(text):
            continue
        url = _extract_source_url(text)
        title = _extract_title(text) or path.stem
        content = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()
        content = content[:_MAX_CONTENT_CHARS]
        lessons.append({"url": url, "title": title, "content": content, "_course": course_slug})
    return lessons


def load_domain_lessons(domain: int) -> list[dict]:
    """도메인에 해당하는 모든 코스의 레슨을 중복 없이 반환."""
    seen_urls: set[str] = set()
    lessons = []
    for slug in DOMAIN_COURSES.get(domain, []):
        for lesson in load_course_lessons(slug):
            key = lesson["url"] or lesson["title"]
            if key in seen_urls:
                continue
            seen_urls.add(key)
            lessons.append(lesson)
    return lessons


# ── 키워드 스코어링 ────────────────────────────────────────────

_STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or",
    "is", "are", "be", "was", "with", "by", "as", "it", "its", "this",
    "that", "from", "how", "what", "when", "use", "using", "used", "you",
    "your", "can", "will", "not", "but", "which", "all", "more", "also",
    "than", "been", "have", "has", "had", "they", "their", "there",
}


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z][a-z0-9_-]*", text.lower())
    return {t for t in tokens if t not in _STOP_WORDS and len(t) > 2}


def _score_lesson(lesson: dict, concept_keywords: set[str]) -> int:
    haystack = (lesson["title"] + " " + lesson["content"]).lower()
    return sum(1 for kw in concept_keywords if kw in haystack)


def select_lessons(lessons: list[dict], concept_name: str, description: str, tags: list[str]) -> list[dict]:
    """키워드 스코어 상위 N개 레슨 선택. 매칭 없으면 상위 2개 fallback."""
    kw_text = f"{concept_name} {description} {' '.join(tags)}"
    kws = _tokenize(kw_text)
    scored = sorted(
        ((  _score_lesson(l, kws), l) for l in lessons),
        key=lambda x: x[0],
        reverse=True,
    )
    top = [l for score, l in scored if score > 0][:_MAX_LESSONS_PER_CONCEPT]
    if not top:
        # 매칭 없으면 도메인 대표 레슨 2개로 fallback
        top = [l for _, l in scored[:2]]
    return top


# ── 메인 ──────────────────────────────────────────────────────

@app.command()
def main(
    exam: str = typer.Option("CCA", "--exam", help="자격증 ID"),
    force: bool = typer.Option(False, "--force", help="이미 존재하는 doc도 재생성"),
    dry_run: bool = typer.Option(False, "--dry-run", help="레슨 매칭만 확인 (S3 저장 안 함)"),
    concept_id: str = typer.Option("", "--concept-id", help="특정 concept만 처리"),
    domain: int = typer.Option(0, "--domain", help="특정 도메인만 처리 (0=전체)"),
) -> None:
    concepts = get_all_concepts(exam_id=exam)
    if concept_id:
        concepts = [c for c in concepts if c.concept_id == concept_id]
        if not concepts:
            logger.error(f"concept_id '{concept_id}'를 찾을 수 없습니다.")
            raise typer.Exit(1)
    if domain:
        concepts = [c for c in concepts if c.domain == domain]

    logger.info(f"총 {len(concepts)}개 concept 처리 (exam={exam})")

    # 도메인별 레슨 사전 로드 (파일 I/O 최소화)
    domain_lessons: dict[int, list[dict]] = {}
    for d in range(1, 6):
        lessons = load_domain_lessons(d)
        domain_lessons[d] = lessons
        logger.info(f"  Domain {d}: {len(lessons)}개 레슨")

    ok = skipped = errors = 0

    for i, concept in enumerate(concepts, 1):
        logger.info(
            f"[{i}/{len(concepts)}] {concept.name}"
            f" | id={concept.concept_id} | domain={concept.domain}"
        )

        if not force and not dry_run and doc_exists(concept.concept_id, exam_id=exam):
            logger.info("  이미 존재, 스킵")
            skipped += 1
            continue

        lessons = domain_lessons.get(concept.domain, [])
        pages = select_lessons(lessons, concept.name, concept.description, concept.tags)

        if not pages:
            logger.warning("  관련 레슨 없음, 스킵")
            errors += 1
            continue

        for p in pages:
            logger.info(f"  ✓ [{p['_course']}] {p['title']} ({len(p['content'])}자)")

        if dry_run:
            ok += 1
            continue

        # 청킹
        # pages에서 내부 메타키 제거 후 저장
        clean_pages = [{"url": p["url"], "title": p["title"], "content": p["content"]} for p in pages]
        chunks = chunk_pages(clean_pages, concept.concept_id)

        # 요약
        raw = "\n\n---\n\n".join(f"## {p['title']}\n\n{p['content']}" for p in clean_pages)
        try:
            summary = summarize_doc_content(concept.name, raw)
            logger.info(f"  → 요약 {len(summary)}자")
        except Exception as e:
            logger.error(f"  요약 실패: {e}")
            summary = ""
            errors += 1

        now = datetime.now(UTC).isoformat()
        save_doc(concept.concept_id, {
            "concept_id": concept.concept_id,
            "concept_name": concept.name,
            "summary": summary,
            "chunks": chunks,
            "pages": clean_pages,
            "fetched_at": now,
            "chunked_at": now,
            "summarized_at": now if summary else "",
        }, exam_id=exam)
        logger.info("  → S3 저장 완료")
        ok += 1
        time.sleep(_BEDROCK_DELAY)

    logger.info(f"\n완료: 성공 {ok} / 스킵 {skipped} / 실패 {errors}")


if __name__ == "__main__":
    app()
