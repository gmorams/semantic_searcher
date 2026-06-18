"""Baseline vectorial: embeddings + similitud coseno."""

from db.vector_store import VectorStore
from processing.embedder import Embedder
from retrieval.base import BaseRetriever, format_chroma_results
import settings


class DenseRetriever(BaseRetriever):
    name = "dense"
    description = "Cerca vectorial pura (baseline)"

    def __init__(self):
        self.vector_store = VectorStore()
        self.embedder = Embedder()

    def search(self, query, top_k=None):
        top_k = top_k or settings.TOP_K
        embedding = self.embedder.embed(query)
        results = self.vector_store.search(embedding, n_results=top_k)
        return {
            "query": query,
            "enriched_query": query,
            "ontology_context": "",
            "entities": [],
            "results": format_chroma_results(results, "dense"),
        }
