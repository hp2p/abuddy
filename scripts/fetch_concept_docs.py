#!/usr/bin/env python
"""
각 concept 노드에 대해 AWS 공식 문서를 수집·청킹·요약하여 S3에 저장.

Tavily Search API로 docs.aws.amazon.com 검색 → 본문 수집 → 청킹 + Bedrock 요약 → S3 저장.

저장 위치: s3://abuddy-data/docs/{concept_id}.json
형식: { concept_id, concept_name, summary, chunks, pages, fetched_at, chunked_at, summarized_at }

사전 준비: .env에 TAVILY_API_KEY 설정 (https://app.tavily.com)

사용법:
  uv run scripts/fetch_concept_docs.py                 # 전체 수집 (이미 수집된 건 스킵)
  uv run scripts/fetch_concept_docs.py --force         # 전체 재수집
  uv run scripts/fetch_concept_docs.py --concept-id d1-rag
  uv run scripts/fetch_concept_docs.py --dry-run       # URL 확인만 (저장 안 함)
  uv run scripts/fetch_concept_docs.py --chunk-only    # 기존 수집분에 청킹만 추가
  uv run scripts/fetch_concept_docs.py --summarize-only  # 기존 수집분에 요약만 추가
"""
import sys
import time
from datetime import UTC, datetime

import httpx
import typer
from loguru import logger

sys.path.insert(0, "src")
from abuddy.config import settings
from abuddy.services.bedrock import summarize_doc_content
from abuddy.services.concept_docs import chunk_pages, doc_exists, load_doc, load_raw_pages, save_doc
from abuddy.services.concept_graph import get_all_concepts

app = typer.Typer()

_TAVILY_URL = "https://api.tavily.com/search"
_SEARCH_DELAY = 1.0   # Tavily 요청 간격 (초)
_BEDROCK_DELAY = 0.5  # Bedrock 요청 간격 (초)
_MAX_RESULTS = 3      # concept당 최대 수집 페이지 수
_MAX_CONTENT_CHARS = 8000  # 페이지당 저장할 최대 글자 수

_SOURCE_DOMAINS = {
    "aws": ["docs.aws.amazon.com"],
    "anthropic": ["docs.anthropic.com"],
}


def _search_docs(concept_name: str, services: list[str], client: httpx.Client, source: str) -> list[dict]:
    """Tavily로 지정된 도메인 검색, [{url, title, content}] 반환."""
    services_str = " ".join(services[:2]) if services else ""
    query = f"{concept_name} {services_str}".strip()
    include_domains = _SOURCE_DOMAINS.get(source, _SOURCE_DOMAINS["aws"])
    logger.info(f"  쿼리: {query} (source={source}, domains={include_domains})")

    try:
        r = client.post(
            _TAVILY_URL,
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "search_depth": "advanced",
                "include_domains": include_domains,
                "include_raw_content": False,
                "max_results": _MAX_RESULTS,
            },
            timeout=30,
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(f"  Tavily API 오류 {e.response.status_code}: {e.response.text[:200]}")
        return []
    except Exception as e:
        logger.error(f"  Tavily 요청 실패: {e}")
        return []

    pages = []
    for result in r.json().get("results", []):
        content = (result.get("content") or "").strip()
        if len(content) < 100:
            continue
        pages.append({
            "url": result.get("url", ""),
            "title": result.get("title", ""),
            "content": content[:_MAX_CONTENT_CHARS],
        })
    return pages


_EXAM_DEFAULT_SOURCE = {
    "aip-c01": "aws",
    "claude-cert": "anthropic",
}


@app.command()
def main(
    force: bool = typer.Option(False, "--force", help="이미 수집된 것도 재처리"),
    concept_id: str = typer.Option("", "--concept-id", help="특정 concept만 처리"),
    dry_run: bool = typer.Option(False, "--dry-run", help="검색 결과 확인만 (저장 안 함)"),
    chunk_only: bool = typer.Option(False, "--chunk-only", help="수집/요약 스킵, 청킹만 추가"),
    summarize_only: bool = typer.Option(False, "--summarize-only", help="수집/청킹 스킵, 요약만 추가"),
    exam: str = typer.Option("aip-c01", "--exam", help="자격증 ID (예: aip-c01, claude-cert)"),
    source: str = typer.Option("", "--source", help="문서 소스: aws (docs.aws.amazon.com) | anthropic (docs.anthropic.com). 기본값은 exam에 따라 자동 선택"),
):
    if chunk_only and summarize_only:
        logger.error("--chunk-only와 --summarize-only는 동시에 사용할 수 없습니다.")
        raise typer.Exit(1)

    if source and source not in _SOURCE_DOMAINS:
        logger.error(f"--source는 {list(_SOURCE_DOMAINS.keys())} 중 하나여야 합니다.")
        raise typer.Exit(1)
    resolved_source = source or _EXAM_DEFAULT_SOURCE.get(exam, "aws")
    logger.info(f"문서 소스: {resolved_source} ({_SOURCE_DOMAINS[resolved_source]})")

    if not (chunk_only or summarize_only) and not settings.tavily_api_key:
        logger.error("TAVILY_API_KEY가 설정되지 않았습니다. .env를 확인하세요.")
        raise typer.Exit(1)

    concepts = get_all_concepts(exam_id=exam)
    if concept_id:
        concepts = [c for c in concepts if c.concept_id == concept_id]
        if not concepts:
            logger.error(f"concept_id '{concept_id}'를 찾을 수 없습니다.")
            raise typer.Exit(1)

    mode = "chunk-only" if chunk_only else "summarize-only" if summarize_only else "full"
    logger.info(f"총 {len(concepts)}개 concept 처리 시작 (mode={mode}, exam={exam}, source={resolved_source})")
    ok = skipped = errors = 0

    with httpx.Client(timeout=30) as client:
        for i, concept in enumerate(concepts, 1):
            services_str = ", ".join(concept.aws_services) if concept.aws_services else "-"
            logger.info(
                f"[{i}/{len(concepts)}] {concept.name}"
                f" | id={concept.concept_id} | domain={concept.domain}"
                f" | services: {services_str}"
            )

            # ── chunk-only: 기존 doc에 청킹만 추가 ─────────────
            if chunk_only:
                doc = load_doc(concept.concept_id, exam_id=exam)
                if not doc:
                    logger.warning("  저장된 문서 없음, 스킵")
                    skipped += 1
                    continue
                if not force and doc.get("chunked_at"):
                    logger.info("  이미 청킹됨, 스킵")
                    skipped += 1
                    continue
                doc["chunks"] = chunk_pages(doc.get("pages", []), concept.concept_id)
                doc["chunked_at"] = datetime.now(UTC).isoformat()
                save_doc(concept.concept_id, doc, exam_id=exam)
                logger.info(f"  → {len(doc['chunks'])}개 청크 저장 완료")
                ok += 1
                continue

            # ── summarize-only: 기존 doc에 요약만 추가 ──────────
            if summarize_only:
                doc = load_doc(concept.concept_id, exam_id=exam)
                if not doc:
                    logger.warning("  저장된 문서 없음, 스킵")
                    skipped += 1
                    continue
                if not force and doc.get("summarized_at"):
                    logger.info("  이미 요약됨, 스킵")
                    skipped += 1
                    continue
                raw = load_raw_pages(concept.concept_id, exam_id=exam)
                try:
                    doc["summary"] = summarize_doc_content(concept.name, raw)
                    doc["summarized_at"] = datetime.now(UTC).isoformat()
                    save_doc(concept.concept_id, doc, exam_id=exam)
                    logger.info(f"  → 요약 저장 완료 ({len(doc['summary'])}자)")
                    ok += 1
                except Exception as e:
                    logger.error(f"  요약 실패: {e}")
                    errors += 1
                time.sleep(_BEDROCK_DELAY)
                continue

            # ── full: 수집 + 청킹 + 요약 ────────────────────────
            if not force and not dry_run and doc_exists(concept.concept_id, exam_id=exam):
                logger.info("  이미 수집됨, 스킵")
                skipped += 1
                continue

            pages = _search_docs(concept.name, concept.aws_services, client, resolved_source)
            if not pages:
                logger.warning("  검색 결과 없음")
                errors += 1
                time.sleep(_SEARCH_DELAY)
                continue

            for page in pages:
                logger.info(f"  ✓ {page['title']} ({len(page['content'])}자) — {page['url']}")

            if dry_run:
                ok += 1
                time.sleep(_SEARCH_DELAY)
                continue

            # 청킹
            chunks = chunk_pages(pages, concept.concept_id)
            logger.info(f"  → {len(chunks)}개 청크 생성")

            # 요약
            raw = "\n\n---\n\n".join(
                f"## {p['title']}\n\n{p['content']}" for p in pages
            )
            try:
                summary = summarize_doc_content(concept.name, raw)
                logger.info(f"  → 요약 생성 ({len(summary)}자)")
            except Exception as e:
                logger.error(f"  요약 실패: {e}")
                summary = ""
            time.sleep(_BEDROCK_DELAY)

            now = datetime.now(UTC).isoformat()
            save_doc(concept.concept_id, {
                "concept_id": concept.concept_id,
                "concept_name": concept.name,
                "summary": summary,
                "chunks": chunks,
                "pages": pages,
                "fetched_at": now,
                "chunked_at": now,
                "summarized_at": now if summary else "",
            }, exam_id=exam)
            logger.info("  → S3 저장 완료")
            ok += 1
            time.sleep(_SEARCH_DELAY)

    logger.info(f"\n완료: 성공 {ok} / 스킵 {skipped} / 실패 {errors}")


if __name__ == "__main__":
    app()
