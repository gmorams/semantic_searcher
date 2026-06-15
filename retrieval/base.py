"""Interficie comuna per a totes les estrategies de cerca.

Cada retriever implementa `search(query, top_k)` i retorna un dict amb:
    query            consulta original
    enriched_query   consulta despres de l'expansio (si aplica)
    ontology_context context ontologic per al prompt (si aplica)
    entities         entitats enllacades [(etiqueta, url)] (si aplica)
    results          llista de resultats normalitzats

Cada resultat te: rank, title, section, source, content, preview,
similarity, score, retrieval_source i boosts (llista d'etiquetes).
"""


def make_item(doc, meta, score, retrieval_source, rank=0):
    return {
        "rank": rank,
        "title": meta.get("title", ""),
        "section": meta.get("section", ""),
        "source": meta.get("source", ""),
        "content": doc,
        "preview": doc[:240] + "..." if len(doc) > 240 else doc,
        "similarity": round(score, 4),
        "score": round(score, 4),
        "retrieval_source": retrieval_source,
        "boosts": [],
    }


def format_chroma_results(results, retrieval_source):
    """Converteix la resposta de ChromaDB al format de resultats comu."""
    if not results or not results.get("documents") or not results["documents"][0]:
        return []
    items = []
    for rank, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ), start=1):
        similarity = max(0.0, 1.0 - dist)
        items.append(make_item(doc, meta, similarity, retrieval_source, rank))
    return items


def normalize_url(url):
    """Normalitza una URL per a comparacions (sense fragment ni barra final)."""
    return (url or "").split("#")[0].split("?")[0].rstrip("/")


class BaseRetriever:
    name = "base"
    description = ""

    def search(self, query, top_k=None):
        raise NotImplementedError
