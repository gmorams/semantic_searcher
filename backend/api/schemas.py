"""Modelos Pydantic: contrato HTTP del backend."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class RetrievedDoc(BaseModel):
    rank: int
    title: str
    section: str
    source: str
    preview: str
    score: float
    similarity: float
    retrieval_source: str
    boosts: List[str] = []


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    mode: str = "hybrid"
    history: List[Message] = []


class AskResponse(BaseModel):
    answer: str
    mode: str
    sources: List[str]
    search_question: str
    enriched_query: str
    ontology_context: Optional[str] = None
    api_context: Optional[str] = None
    entities: List[Tuple[str, str]] = []
    num_docs_retrieved: int
    retrieved_docs: List[RetrievedDoc]


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    mode: str = "hybrid"
    top_k: int = Field(5, ge=1, le=20)


class SearchResponse(BaseModel):
    query: str
    enriched_query: str
    mode: str
    ontology_context: Optional[str] = None
    entities: List[Tuple[str, str]] = []
    results: List[RetrievedDoc]


class CompareRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k_per_mode: int = Field(3, ge=1, le=10)


class CompareResponse(BaseModel):
    query: str
    modes: Dict[str, List[str]]


class AskAllRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: List[Message] = []


class AskAllResponse(BaseModel):
    question: str
    responses: Dict[str, AskResponse]
    errors: Dict[str, str] = {}


class OntologyClass(BaseModel):
    name: str
    instance_count: int


class OntologyConcept(BaseModel):
    label: str
    type: str
    code: Optional[str] = None
    url: Optional[str] = None
    synonyms: List[str] = []
    related: List[str] = []
    weight: Optional[float] = None


class StatsResponse(BaseModel):
    document_count: int
    ontology_triples: int
    ontology_instances: int
    ontology_classes: int
    instances_by_type: Dict[str, int]
    available_modes: Dict[str, str]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
