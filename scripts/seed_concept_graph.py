#!/usr/bin/env python
"""
aip-c01-exam-guide.json을 Task 단위로 읽어 Bedrock 호출, 개념 그래프를 S3에 저장.
Task당 약 10~20초 소요. 총 ~25개 Task → 약 5~8분.

체크포인팅: Task별 결과를 .checkpoints/ 에 저장.
중단 후 재실행하면 완료된 Task는 스킵합니다.

사전 준비: aip-c01-exam-guide.json 이 프로젝트 루트에 있어야 합니다.

사용법:
  uv run scripts/seed_concept_graph.py           # 실행 (완료된 Task 스킵)
  uv run scripts/seed_concept_graph.py --force   # 체크포인트 무시하고 전체 재실행
"""
import sys
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import orjson
import typer
from loguru import logger

sys.path.insert(0, "src")
from abuddy.models.concept import Concept, ConceptEdge
from abuddy.services.bedrock import extract_concept_graph_for_domain
from abuddy.services.concept_graph import save_graph

EXAM_GUIDE_JSON = Path("aip-c01-exam-guide.json")
CHECKPOINT_DIR = Path(".checkpoints")


@dataclass
class Chunk:
    domain: int
    task: str   # "1.1", "1.2", ...
    label: str
    content: str

    @property
    def checkpoint_path(self) -> Path:
        safe_task = self.task.replace(".", "_")
        return CHECKPOINT_DIR / f"task_{safe_task}.json"


def load_chunks_from_json() -> list[Chunk]:
    data = orjson.loads(EXAM_GUIDE_JSON.read_bytes())
    chunks = []
    for domain in data["domains"]:
        domain_id = domain["id"]
        domain_title = domain["title"]
        for task in domain["tasks"]:
            task_id = task["id"]
            task_title = task["title"]
            content = _format_task_content(domain_id, domain_title, task)
            chunks.append(Chunk(
                domain=domain_id,
                task=task_id,
                label=f"Domain {domain_id} / Task {task_id}: {task_title}",
                content=content,
            ))
    return chunks


def _format_task_content(domain_id: int, domain_title: str, task: dict) -> str:
    lines = [
        f"Domain {domain_id}: {domain_title}",
        f"Task {task['id']}: {task['title']}",
        "",
    ]
    for skill in task["skills"]:
        lines.append(f"Skill {skill['id']}: {skill['description']}")
        for technique in skill.get("techniques", []):
            lines.append(f"  - {technique}")
        lines.append("")
    return "\n".join(lines)


def save_checkpoint(chunk: Chunk, result: dict) -> None:
    CHECKPOINT_DIR.mkdir(exist_ok=True)
    chunk.checkpoint_path.write_bytes(orjson.dumps(result, option=orjson.OPT_INDENT_2))
    logger.debug(f"체크포인트 저장: {chunk.checkpoint_path.name}")


def load_checkpoint(chunk: Chunk) -> dict | None:
    if chunk.checkpoint_path.exists():
        return orjson.loads(chunk.checkpoint_path.read_bytes())
    return None


def clear_checkpoints() -> None:
    if CHECKPOINT_DIR.exists():
        for f in CHECKPOINT_DIR.glob("task_*.json"):
            f.unlink()
        logger.info("체크포인트 초기화 완료")


def merge_results(all_results: list[tuple[Chunk, dict]]) -> nx.DiGraph:
    g = nx.DiGraph()
    seen_ids: set[str] = set()

    for chunk, data in all_results:
        for node_data in data.get("nodes", []):
            try:
                c = Concept(**node_data)
                if c.concept_id in seen_ids:
                    logger.debug(f"중복 스킵: {c.concept_id}")
                    continue
                g.add_node(c.concept_id, **c.model_dump())
                seen_ids.add(c.concept_id)
            except Exception as e:
                logger.warning(f"노드 파싱 실패 ({chunk.label}): {e} — {node_data}")

    edge_count = 0
    for chunk, data in all_results:
        for edge_data in data.get("edges", []):
            try:
                e = ConceptEdge(**edge_data)
                if e.source_id in g and e.target_id in g:
                    g.add_edge(e.source_id, e.target_id, relation=e.relation, weight=e.weight)
                    edge_count += 1
            except Exception:
                pass

    logger.info(f"엣지 {edge_count}개 연결 완료")
    return g


app = typer.Typer()


@app.command()
def main(force: bool = typer.Option(False, "--force", help="체크포인트 무시하고 전체 재실행")):
    if not EXAM_GUIDE_JSON.exists():
        logger.error(f"{EXAM_GUIDE_JSON} 파일이 없습니다.")
        raise typer.Exit(1)

    if force:
        clear_checkpoints()

    chunks = load_chunks_from_json()
    logger.info(f"총 {len(chunks)}개 Task 청크 로드 완료")

    all_results: list[tuple[Chunk, dict]] = []
    skipped = 0

    for i, chunk in enumerate(chunks, 1):
        cached = load_checkpoint(chunk)
        if cached is not None:
            node_count = len(cached.get("nodes", []))
            logger.info(f"[{i}/{len(chunks)}] {chunk.label} ← 체크포인트 로드 (노드 {node_count}개)")
            all_results.append((chunk, cached))
            skipped += 1
            continue

        logger.info(f"[{i}/{len(chunks)}] {chunk.label} 처리 중...")
        try:
            result = extract_concept_graph_for_domain(chunk.domain, chunk.content)
            node_count = len(result.get("nodes", []))
            edge_count = len(result.get("edges", []))
            logger.info(f"[{i}/{len(chunks)}] 완료 — 노드 {node_count}개, 엣지 {edge_count}개")
            save_checkpoint(chunk, result)
            all_results.append((chunk, result))
        except Exception as e:
            logger.error(f"[{i}/{len(chunks)}] {chunk.label} 실패: {e}")

    if not all_results:
        logger.error("추출된 결과가 없습니다.")
        raise typer.Exit(1)

    if skipped:
        logger.info(f"체크포인트에서 로드: {skipped}개 / Bedrock 호출: {len(all_results) - skipped}개")

    logger.info("그래프 병합 중...")
    g = merge_results(all_results)
    logger.info(f"최종 그래프: 노드 {g.number_of_nodes()}개, 엣지 {g.number_of_edges()}개")

    save_graph(g)
    logger.info("S3 저장 완료.")


if __name__ == "__main__":
    app()
