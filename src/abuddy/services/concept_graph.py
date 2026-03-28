"""개념 그래프: networkx + S3 JSON 저장"""
import io

import boto3
import networkx as nx
import orjson
from loguru import logger

from abuddy.config import settings
from abuddy.models.concept import Concept, ConceptEdge, ConceptGraph

_S3_KEY = "graph/concept_graph.json"
_graph: nx.DiGraph | None = None  # 메모리 캐시


def _s3():
    return boto3.client("s3", region_name=settings.aws_region)


def load_graph() -> nx.DiGraph:
    global _graph
    if _graph is not None:
        return _graph

    try:
        obj = _s3().get_object(Bucket=settings.s3_bucket, Key=_S3_KEY)
        data = orjson.loads(obj["Body"].read())
        cg = ConceptGraph(**data)
    except Exception:
        logger.warning("No concept graph found in S3, returning empty graph")
        _graph = nx.DiGraph()
        return _graph

    g = nx.DiGraph()
    for node in cg.nodes:
        g.add_node(node.concept_id, **node.model_dump())
    for edge in cg.edges:
        g.add_edge(edge.source_id, edge.target_id, relation=edge.relation, weight=edge.weight)

    _graph = g
    logger.info(f"Loaded concept graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
    return _graph


def save_graph(g: nx.DiGraph) -> None:
    global _graph
    nodes = [Concept(**g.nodes[n]) for n in g.nodes]
    edges = [
        ConceptEdge(source_id=u, target_id=v, **d)
        for u, v, d in g.edges(data=True)
    ]
    cg = ConceptGraph(nodes=nodes, edges=edges)
    body = orjson.dumps(cg.model_dump(), option=orjson.OPT_INDENT_2)
    _s3().put_object(Bucket=settings.s3_bucket, Key=_S3_KEY, Body=body, ContentType="application/json")
    _graph = g
    logger.info("Saved concept graph to S3")


def get_related_concept_ids(concept_id: str, hops: int = 2) -> list[str]:
    """주어진 concept에서 N-hop 이내 이웃 concept_id 목록"""
    g = load_graph()
    if concept_id not in g:
        return []
    neighbors = set()
    frontier = {concept_id}
    for _ in range(hops):
        next_frontier = set()
        for node in frontier:
            next_frontier.update(g.successors(node))
            next_frontier.update(g.predecessors(node))
        neighbors.update(next_frontier)
        frontier = next_frontier - neighbors
    neighbors.discard(concept_id)
    return list(neighbors)


def get_all_concepts() -> list[Concept]:
    g = load_graph()
    return [Concept(**g.nodes[n]) for n in g.nodes]


def get_concept(concept_id: str) -> Concept | None:
    g = load_graph()
    if concept_id not in g:
        return None
    return Concept(**g.nodes[concept_id])


def invalidate_cache() -> None:
    global _graph
    _graph = None
