"""Interfaz común de los retrievers: cada uno implementa `search(query, top_k)`."""


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
    """Convierte la respuesta de ChromaDB al formato común."""
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
    # sin fragmento, sin query, sin barra final
    return (url or "").split("#")[0].split("?")[0].rstrip("/")


class BaseRetriever:
    name = "base"
    description = ""

    def search(self, query, top_k=None):
        raise NotImplementedError
