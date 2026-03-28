#!/usr/bin/env python
"""
개념 그래프 검사 스크립트.
S3에서 graph를 로드해 구조를 출력합니다.

사용법:
  uv run scripts/inspect_graph.py            # 요약 출력
  uv run scripts/inspect_graph.py --full     # 전체 노드/엣지 출력
  uv run scripts/inspect_graph.py --dump     # S3 원본 JSON 그대로 출력
"""
import sys
from pathlib import Path

import boto3
import orjson
import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich import print as rprint

sys.path.insert(0, "src")
from abuddy.config import settings
from abuddy.services.concept_graph import load_graph, get_all_concepts

console = Console()
app = typer.Typer()

S3_KEY = "graph/concept_graph.json"


def fetch_raw_json() -> dict:
    s3 = boto3.client("s3", region_name=settings.aws_region)
    obj = s3.get_object(Bucket=settings.s3_bucket, Key=S3_KEY)
    return orjson.loads(obj["Body"].read())


@app.command()
def main(
    full: bool = typer.Option(False, "--full", help="전체 노드/엣지 출력"),
    dump: bool = typer.Option(False, "--dump", help="S3 원본 JSON 그대로 출력"),
):
    # S3 원본 JSON 출력
    if dump:
        data = fetch_raw_json()
        console.print_json(orjson.dumps(data).decode())
        return

    # 그래프 로드
    g = load_graph()
    concepts = get_all_concepts()

    console.rule("[bold cyan]개념 그래프 요약[/bold cyan]")
    console.print(f"  S3 위치  : s3://{settings.s3_bucket}/{S3_KEY}")
    console.print(f"  노드(개념): [bold]{g.number_of_nodes()}[/bold]개")
    console.print(f"  엣지(관계): [bold]{g.number_of_edges()}[/bold]개")
    console.print()

    # 도메인별 분포
    console.rule("[bold]도메인별 개념 수[/bold]")
    domain_table = Table("도메인", "제목", "개념 수", show_header=True, header_style="bold magenta")
    domain_titles = {
        1: "Foundation Model Integration",
        2: "Implementation and Integration",
        3: "AI Safety, Security, and Governance",
        4: "Operational Efficiency and Optimization",
        5: "Testing, Validation, and Troubleshooting",
    }
    domain_counts: dict[int, int] = {}
    for c in concepts:
        domain_counts[c.domain] = domain_counts.get(c.domain, 0) + 1
    for d in sorted(domain_counts):
        domain_table.add_row(str(d), domain_titles.get(d, ""), str(domain_counts[d]))
    console.print(domain_table)
    console.print()

    # 엣지 관계 유형별 분포
    console.rule("[bold]엣지 관계 유형[/bold]")
    relation_counts: dict[str, int] = {}
    for _, _, data in g.edges(data=True):
        r = data.get("relation", "unknown")
        relation_counts[r] = relation_counts.get(r, 0) + 1
    rel_table = Table("relation", "count", show_header=True, header_style="bold magenta")
    for rel, cnt in sorted(relation_counts.items(), key=lambda x: -x[1]):
        rel_table.add_row(rel, str(cnt))
    console.print(rel_table)
    console.print()

    # 연결 많은 노드 Top 10
    console.rule("[bold]연결 많은 개념 Top 10[/bold]")
    degree_seq = sorted(g.degree(), key=lambda x: -x[1])[:10]
    top_table = Table("concept_id", "name", "domain", "degree", show_header=True, header_style="bold magenta")
    for node_id, deg in degree_seq:
        node = g.nodes[node_id]
        top_table.add_row(node_id, node.get("name", ""), str(node.get("domain", "")), str(deg))
    console.print(top_table)
    console.print()

    if not full:
        console.print("[dim]전체 목록: --full  |  S3 원본 JSON: --dump[/dim]")
        return

    # 전체 노드 목록
    console.rule("[bold]전체 개념 목록[/bold]")
    node_table = Table("concept_id", "name", "domain", "aws_services", "tags", show_header=True, header_style="bold")
    for c in sorted(concepts, key=lambda x: (x.domain, x.name)):
        node_table.add_row(
            c.concept_id,
            c.name,
            str(c.domain),
            ", ".join(c.aws_services[:3]) + ("..." if len(c.aws_services) > 3 else ""),
            ", ".join(c.tags[:4]),
        )
    console.print(node_table)
    console.print()

    # 전체 엣지 목록
    console.rule("[bold]전체 엣지 목록[/bold]")
    edge_table = Table("source", "target", "relation", "weight", show_header=True, header_style="bold")
    for u, v, data in g.edges(data=True):
        src_name = g.nodes[u].get("name", u)
        tgt_name = g.nodes[v].get("name", v)
        edge_table.add_row(src_name, tgt_name, data.get("relation", ""), str(data.get("weight", "")))
    console.print(edge_table)


if __name__ == "__main__":
    app()
