"""Resolucion de dependencias compartidas (singletons del dominio)."""

from __future__ import annotations

import os
import sys
from functools import lru_cache

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from db.vector_store import VectorStore  # noqa: E402
from ontology.fib_ontology import FIBOntology, get_ontology  # noqa: E402
from agent.rag_chain import RAGChain  # noqa: E402
from retrieval import MODES, get_retriever  # noqa: E402


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    return VectorStore()


@lru_cache(maxsize=1)
def get_ontology_singleton() -> FIBOntology:
    return get_ontology()


@lru_cache(maxsize=len(MODES))
def get_rag_chain(mode: str) -> RAGChain:
    if mode not in MODES:
        raise ValueError(f"Modo de búsqueda desconocido: {mode}")
    return RAGChain(mode=mode)


def get_retriever_cached(mode: str):
    if mode not in MODES:
        raise ValueError(f"Modo de búsqueda desconocido: {mode}")
    return get_retriever(mode)
