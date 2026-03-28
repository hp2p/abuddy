from pydantic import BaseModel, Field
from uuid import uuid4


class Concept(BaseModel):
    concept_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str                    # "RAG", "Amazon Bedrock Knowledge Bases", ...
    domain: int                  # 1-5
    description: str = ""
    aws_services: list[str] = [] # 관련 AWS 서비스
    tags: list[str] = []         # "retrieval", "vector", "embedding", ...


class ConceptEdge(BaseModel):
    source_id: str
    target_id: str
    relation: str  # "requires", "uses", "part_of", "similar_to"
    weight: float = 1.0


class ConceptGraph(BaseModel):
    """networkx 저장/로드용 직렬화 포맷 (S3에 JSON으로 저장)"""
    nodes: list[Concept] = []
    edges: list[ConceptEdge] = []
