"""
Búsqueda guiada por la ontología con reranking controlado: recupera un conjunto
amplio de candidatos, inyecta páginas canónicas de los conceptos/entidades
detectados y aplica boosts transparentes derivados del grafo RDF.
"""

from db.vector_store import VectorStore
from ontology.fib_ontology import get_ontology, normalize
from processing.embedder import Embedder
from retrieval.base import BaseRetriever, format_chroma_results, make_item, normalize_url
from retrieval.entity_linker import extract_entities
import settings

ENTITY_BOOST = 0.45        # coincidencia exacta con la página de la entidad enlazada
SLUG_FACTOR = 0.5          # fracción del peso del concepto para matches parciales
DEGREE_BOOST = 0.15        # subárbol de la titulación detectada
DEGREE_PENALTY = -0.12     # páginas de otras titulaciones
TITLE_FACTOR = 0.25        # extra si el patrón aparece también en el título


class ControlledOntologyRetriever(BaseRetriever):
    name = "controlled"
    description = "Cerca guiada per ontologia: candidats amplis + entity linking + reranking"

    def __init__(self):
        self.vector_store = VectorStore()
        self.embedder = Embedder()
        self.ontology = get_ontology()

    def search(self, query, top_k=None):
        final_k = top_k or settings.TOP_K
        candidate_k = max(final_k * 8, settings.CANDIDATE_K)

        enriched_query = self.ontology.enrich_query(query)
        entities = extract_entities(query)

        # 1. Conjunto amplio de candidatos: consulta original + enriquecida
        candidates = {}
        query_embedding = self.embedder.embed(query)
        searches = [(query_embedding, "dense")]
        if enriched_query != query:
            searches.append((self.embedder.embed(enriched_query), "ontology"))
        for embedding, label in searches:
            raw = self.vector_store.search(embedding, n_results=candidate_k)
            for item in format_chroma_results(raw, label):
                self._add_candidate(candidates, item)

        # 2. Inyección de páginas canónicas (entidades + conceptos detectados)
        canonical_urls = [url for _, url in entities]
        for url, _, _ in self.ontology.intent_resources(query):
            if url not in canonical_urls:
                canonical_urls.append(url)
        for item in self._fetch_canonical_docs(canonical_urls, query_embedding):
            self._add_candidate(candidates, item)

        # 3. Reranking controlado
        reranked = [self._rerank(query, entities, item) for item in candidates.values()]
        reranked.sort(key=lambda item: item["score"], reverse=True)
        for rank, item in enumerate(reranked[:final_k], start=1):
            item["rank"] = rank

        return {
            "query": query,
            "enriched_query": enriched_query,
            "ontology_context": self.ontology.ontology_context(query),
            "entities": entities,
            "results": reranked[:final_k],
        }

    def _add_candidate(self, candidates, item):
        key = (normalize_url(item["source"]), item["content"][:120])
        if key not in candidates or item["similarity"] > candidates[key]["similarity"]:
            candidates[key] = item

    def _fetch_canonical_docs(self, urls, query_embedding):
        """Recupera de ChromaDB los chunks de las páginas canónicas.

        La similitud asignada es la coseno real entre la consulta y el embedding
        almacenado de cada chunk — nunca un valor inventado.
        """
        import numpy as np

        q = np.asarray(query_embedding, dtype=float)
        q_norm = np.linalg.norm(q) or 1.0

        items = []
        for url in urls:
            try:
                raw = self.vector_store.collection.get(
                    where={"source": url},
                    limit=3,
                    include=["documents", "metadatas", "embeddings"],
                )
            except Exception:
                continue
            docs = raw.get("documents") or []
            metas = raw.get("metadatas") or []
            embs = raw.get("embeddings")
            embs = embs if embs is not None else [None] * len(docs)
            for doc, meta, emb in zip(docs, metas, embs):
                similarity = 0.0
                if emb is not None:
                    e = np.asarray(emb, dtype=float)
                    denom = (np.linalg.norm(e) or 1.0) * q_norm
                    similarity = max(0.0, float(np.dot(q, e) / denom))
                items.append(make_item(doc, meta, similarity, "canonical"))
        return items

    def _rerank(self, query, entities, item):
        item = dict(item)
        score = item["similarity"]
        boosts = []

        source_norm = normalize_url(item["source"])
        haystack = normalize(f"{item['title']} {item['section']} {item['source']}")
        title_norm = normalize(item["title"])

        # (a) Entity linking: coincidencia exacta con la página de la entidad
        for label, url in entities:
            if source_norm == normalize_url(url):
                score += ENTITY_BOOST
                boosts.append(f"entitat:{label}")

        # (b) Recurso canónico de los conceptos detectados (peso de la ontología)
        for url, weight, label in self.ontology.intent_resources(query):
            if source_norm == normalize_url(url):
                score += weight
                boosts.append(f"concepte:{label}")

        # (c) Patrones de URL (fib:patroUrl) como match parcial
        for slug, weight, label in self.ontology.boost_rules(query):
            slug_norm = normalize(slug)
            if slug_norm in haystack:
                score += weight * SLUG_FACTOR
                boosts.append(f"patro:{label}")
                if slug_norm in title_norm:
                    score += weight * TITLE_FACTOR
                    boosts.append(f"titol:{label}")

        # (d) Scoping por titulación (derivado de las instancias fib:Grau/Master)
        matched_degrees = self.ontology.matched_degrees(query)
        if len(matched_degrees) == 1:
            degree = matched_degrees[0]
            degree_url = normalize_url(degree["url"])
            if source_norm.startswith(degree_url):
                score += DEGREE_BOOST
                boosts.append(f"titulacio:{degree['code']}")
            else:
                for other_url, other in self.ontology.degree_urls().items():
                    if other["code"] != degree["code"] and source_norm.startswith(normalize_url(other_url)):
                        score += DEGREE_PENALTY
                        boosts.append(f"penalitzacio:{other['code']}")
                        break

        item["score"] = round(score, 4)
        item["boosts"] = boosts
        return item
