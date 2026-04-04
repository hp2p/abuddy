"""개념 그래프: networkx + S3 JSON 저장"""
import boto3
import networkx as nx
import orjson
from loguru import logger

from abuddy.config import settings
from abuddy.models.concept import Concept, ConceptEdge, ConceptGraph

_graphs: dict[str, nx.DiGraph] = {}  # exam_id → DiGraph 캐시


def _s3():
    return boto3.client("s3", region_name=settings.aws_region)


def _s3_key(exam_id: str) -> str:
    return f"{exam_id}/graph/concept_graph.json"


def load_graph(exam_id: str | None = None) -> nx.DiGraph:
    eid = exam_id or settings.active_exam
    if eid in _graphs:
        return _graphs[eid]

    try:
        obj = _s3().get_object(Bucket=settings.s3_bucket, Key=_s3_key(eid))
        data = orjson.loads(obj["Body"].read())
        cg = ConceptGraph(**data)
    except Exception:
        logger.warning(f"No concept graph found in S3 for exam={eid}, returning empty graph")
        _graphs[eid] = nx.DiGraph()
        return _graphs[eid]

    g = nx.DiGraph()
    for node in cg.nodes:
        g.add_node(node.concept_id, **node.model_dump())
    for edge in cg.edges:
        g.add_edge(edge.source_id, edge.target_id, relation=edge.relation, weight=edge.weight)

    _graphs[eid] = g
    logger.info(f"Loaded concept graph [{eid}]: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
    return _graphs[eid]


def save_graph(g: nx.DiGraph, exam_id: str | None = None) -> None:
    eid = exam_id or settings.active_exam
    nodes = [Concept(**g.nodes[n]) for n in g.nodes]
    edges = [
        ConceptEdge(source_id=u, target_id=v, **d)
        for u, v, d in g.edges(data=True)
    ]
    cg = ConceptGraph(nodes=nodes, edges=edges)
    body = orjson.dumps(cg.model_dump(), option=orjson.OPT_INDENT_2)
    _s3().put_object(Bucket=settings.s3_bucket, Key=_s3_key(eid), Body=body, ContentType="application/json")
    _graphs[eid] = g
    logger.info(f"Saved concept graph [{eid}] to S3")


def get_related_concept_ids(concept_id: str, hops: int = 2, exam_id: str | None = None) -> list[str]:
    """주어진 concept에서 N-hop 이내 이웃 concept_id 목록"""
    g = load_graph(exam_id)
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


def get_all_concepts(exam_id: str | None = None) -> list[Concept]:
    g = load_graph(exam_id)
    return [Concept(**g.nodes[n]) for n in g.nodes]


def get_concept(concept_id: str, exam_id: str | None = None) -> Concept | None:
    g = load_graph(exam_id)
    if concept_id not in g:
        return None
    return Concept(**g.nodes[concept_id])


def invalidate_cache(exam_id: str | None = None) -> None:
    if exam_id:
        _graphs.pop(exam_id, None)
    else:
        _graphs.clear()
