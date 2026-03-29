#!/usr/bin/env python
"""
Haiku가 생성한 요약 품질을 Sonnet이 검토.

10개의 concept 요약을 무작위 샘플링해서 Sonnet이 각각 평가:
- 정확성: AWS 공식 문서 내용과 일치하는가
- 완결성: 시험 핵심 포인트를 빠뜨리지 않았는가
- 집중도: 불필요한 내용 없이 AIP-C01 관련 내용만 담았는가
- 총점: 1-10점

사용법:
  uv run scripts/review_summaries.py            # 무작위 10개
  uv run scripts/review_summaries.py --count 5  # 무작위 5개
  uv run scripts/review_summaries.py --domain 1 # 도메인 1에서 샘플링
"""
import random
import sys
import time

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.insert(0, "src")
from abuddy.config import settings
from abuddy.services.bedrock import _converse
from abuddy.services.concept_docs import load_doc
from abuddy.services.concept_graph import get_all_concepts

app = typer.Typer()
console = Console()

_REVIEW_SYSTEM = """\
You are a senior AWS certification exam expert reviewing study material quality.
Respond only with valid JSON, no markdown fences."""

_REVIEW_TEMPLATE = """\
You are reviewing a summary of AWS documentation written by an AI for AIP-C01 exam preparation.

Concept: {concept_name}
Domain: {domain}
Related AWS services: {services}

Original AWS documentation (source material):
{raw_pages}

Generated summary to review:
{summary}

Evaluate the summary on these criteria and respond with JSON:
{{
  "accuracy": {{
    "score": <1-10>,
    "comment": "<what is correct or incorrect>"
  }},
  "completeness": {{
    "score": <1-10>,
    "comment": "<what key exam points are covered or missing>"
  }},
  "focus": {{
    "score": <1-10>,
    "comment": "<is it focused on AIP-C01 relevant content>"
  }},
  "overall": <1-10>,
  "missing_points": ["<important point not in summary>", ...],
  "recommendation": "keep | revise | regenerate"
}}"""


@app.command()
def main(
    count: int = typer.Option(10, "--count", help="검토할 concept 수"),
    domain: int = typer.Option(0, "--domain", help="특정 도메인만 (0=전체)"),
    seed: int = typer.Option(42, "--seed", help="랜덤 시드"),
):
    concepts = get_all_concepts()
    if domain:
        concepts = [c for c in concepts if c.domain == domain]

    # 요약이 있는 것만 필터
    candidates = []
    for c in concepts:
        doc = load_doc(c.concept_id)
        if doc and doc.get("summary"):
            candidates.append((c, doc))

    if not candidates:
        logger.error("요약이 저장된 concept이 없습니다. --summarize-only를 먼저 실행하세요.")
        raise typer.Exit(1)

    random.seed(seed)
    samples = random.sample(candidates, min(count, len(candidates)))
    logger.info(f"총 {len(candidates)}개 중 {len(samples)}개 무작위 선택 (seed={seed})")

    results = []
    for i, (concept, doc) in enumerate(samples, 1):
        services_str = ", ".join(concept.aws_services) if concept.aws_services else "-"
        logger.info(f"[{i}/{len(samples)}] {concept.name} 검토 중...")

        raw_pages = "\n\n---\n\n".join(
            f"## {p['title']}\n\n{p['content']}" for p in doc.get("pages", [])
        )

        prompt = _REVIEW_TEMPLATE.format(
            concept_name=concept.name,
            domain=concept.domain,
            services=services_str,
            raw_pages=raw_pages[:24000],
            summary=doc["summary"],
        )

        try:
            import orjson
            raw = _converse(settings.bedrock_smart_model_id, _REVIEW_SYSTEM, prompt, max_tokens=1024)
            review = orjson.loads(raw)
            results.append((concept, doc["summary"], review))
        except Exception as e:
            logger.error(f"  검토 실패: {e}")

        time.sleep(0.5)

    # ── 결과 출력 ────────────────────────────────────────────
    console.print(f"\n[bold]Sonnet 요약 품질 검토 결과[/bold] ({len(results)}/{len(samples)}개)\n")

    scores = []
    for concept, summary, review in results:
        overall = review.get("overall", 0)
        scores.append(overall)
        recommendation = review.get("recommendation", "?")
        rec_color = {"keep": "green", "revise": "yellow", "regenerate": "red"}.get(recommendation, "white")

        console.print(Panel(
            f"[bold]{concept.name}[/bold]  (domain={concept.domain})\n"
            f"추천: [{rec_color}]{recommendation.upper()}[/{rec_color}]  |  종합: {overall}/10\n\n"
            f"[dim]요약 미리보기:[/dim] {summary[:150]}...\n\n"
            f"  정확성  {review['accuracy']['score']}/10  — {review['accuracy']['comment']}\n"
            f"  완결성  {review['completeness']['score']}/10  — {review['completeness']['comment']}\n"
            f"  집중도  {review['focus']['score']}/10  — {review['focus']['comment']}\n"
            + (
                "\n  [yellow]누락 포인트:[/yellow] " + ", ".join(review.get("missing_points", []))
                if review.get("missing_points") else ""
            ),
            title=f"[{rec_color}]{concept.concept_id}[/{rec_color}]",
        ))

    # ── 요약 통계 테이블 ─────────────────────────────────────
    table = Table(title="전체 요약")
    table.add_column("항목")
    table.add_column("값", justify="right")
    table.add_row("평균 종합 점수", f"{sum(scores)/len(scores):.1f}/10" if scores else "-")
    table.add_row("keep", str(sum(1 for _, _, r in results if r.get("recommendation") == "keep")))
    table.add_row("revise", str(sum(1 for _, _, r in results if r.get("recommendation") == "revise")))
    table.add_row("regenerate", str(sum(1 for _, _, r in results if r.get("recommendation") == "regenerate")))
    console.print(table)


if __name__ == "__main__":
    app()
