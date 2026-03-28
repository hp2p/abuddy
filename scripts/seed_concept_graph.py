#!/usr/bin/env python
"""
시험 가이드 도메인 페이지에서 개념 그래프를 추출해 S3에 저장.
Bedrock Claude Sonnet 사용 (1회성 작업).

사전 준비: docs/ 폴더에 domain1~5 HTML 또는 텍스트 파일이 있어야 합니다.
없으면 직접 exam guide structured md 파일을 사용합니다.
"""
import sys
from pathlib import Path

import networkx as nx
from loguru import logger

sys.path.insert(0, "src")
from abuddy.models.concept import Concept, ConceptEdge
from abuddy.services import bedrock
from abuddy.services.concept_graph import save_graph

DOCS_DIR = Path("docs")
STRUCTURED_MD = Path("aip-c01-exam-guide-structured.md")


def load_exam_content() -> str:
    # 우선 docs/ 폴더의 모든 텍스트 파일 합치기
    if DOCS_DIR.exists():
        parts = []
        for f in sorted(DOCS_DIR.glob("*.txt")) or sorted(DOCS_DIR.glob("*.md")):
            parts.append(f.read_text(encoding="utf-8"))
        if parts:
            return "\n\n".join(parts)

    # fallback: 다운로드된 structured md
    if STRUCTURED_MD.exists():
        return STRUCTURED_MD.read_text(encoding="utf-8")

    raise FileNotFoundError(
        "No exam content found. Place domain docs in docs/ or ensure "
        "aip-c01-exam-guide-structured.md exists."
    )


def build_graph(raw_data: dict) -> nx.DiGraph:
    g = nx.DiGraph()
    for node_data in raw_data.get("nodes", []):
        c = Concept(**node_data)
        g.add_node(c.concept_id, **c.model_dump())

    for edge_data in raw_data.get("edges", []):
        e = ConceptEdge(**edge_data)
        if e.source_id in g and e.target_id in g:
            g.add_edge(e.source_id, e.target_id, relation=e.relation, weight=e.weight)
        else:
            logger.warning(f"Skipping edge with unknown nodes: {e.source_id} -> {e.target_id}")

    return g


if __name__ == "__main__":
    logger.info("Loading exam guide content...")
    content = load_exam_content()
    logger.info(f"Content length: {len(content)} chars")

    logger.info("Calling Bedrock (Claude Sonnet) to extract concept graph...")
    raw = bedrock.extract_concept_graph(content)

    g = build_graph(raw)
    logger.info(f"Built graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")

    save_graph(g)
    logger.info("Concept graph saved to S3.")

    # 샘플 출력
    for node_id in list(g.nodes)[:5]:
        data = g.nodes[node_id]
        logger.info(f"  [{node_id}] {data.get('name')} (domain {data.get('domain')})")
