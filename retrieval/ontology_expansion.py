"""EXP.2a: expansio ontologica naive de la consulta.

La consulta s'expandeix amb sinonims i conceptes relacionats de l'ontologia
i es fa una unica cerca vectorial amb la consulta enriquida. Es l'estrategia
"naive" que serveix per mesurar si l'expansio per si sola aporta millora.
"""

from db.vector_store import VectorStore
from ontology.fib_ontology import get_ontology
from processing.embedder import Embedder
from retrieval.base import BaseRetriever, format_chroma_results
import settings


class OntologyExpansionRetriever(BaseRetriever):
    name = "ontology"
    description = "Cerca vectorial amb expansio ontologica de la consulta"

    def __init__(self):
        self.vector_store = VectorStore()
        self.embedder = Embedder()
        self.ontology = get_ontology()

    def search(self, query, top_k=None):
        top_k = top_k or settings.TOP_K
        enriched = self.ontology.enrich_query(query)
        embedding = self.embedder.embed(enriched)
        results = self.vector_store.search(embedding, n_results=top_k)
        return {
            "query": query,
            "enriched_query": enriched,
            "ontology_context": self.ontology.ontology_context(query),
            "entities": [],
            "results": format_chroma_results(results, "ontology"),
        }
