from fastapi import APIRouter, HTTPException

from ..deps import get_retriever_cached
from ..schemas import (
    CompareRequest,
    CompareResponse,
    RetrievedDoc,
    SearchRequest,
    SearchResponse,
)

router = APIRouter()


def _to_docs(items: list) -> list[RetrievedDoc]:
    docs: list[RetrievedDoc] = []
    for it in items:
        docs.append(RetrievedDoc(
            rank=it.get("rank", 0),
            title=it.get("title", ""),
            section=it.get("section", ""),
            source=it.get("source", ""),
            preview=it.get("preview", ""),
            score=float(it.get("score", 0.0)),
            similarity=float(it.get("similarity", 0.0)),
            retrieval_source=it.get("retrieval_source", ""),
            boosts=list(it.get("boosts", [])),
        ))
    return docs


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    try:
        retriever = get_retriever_cached(req.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    output = retriever.search(req.query, top_k=req.top_k)
    return SearchResponse(
        query=req.query,
        enriched_query=output.get("enriched_query", req.query),
        mode=req.mode,
        ontology_context=output.get("ontology_context") or None,
        entities=output.get("entities", []),
        results=_to_docs(output["results"]),
    )


@router.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest) -> CompareResponse:
    """Lanza la misma consulta en los cinco modos y devuelve sus top-N URLs."""
    from retrieval import MODES
    from retrieval.base import normalize_url

    by_mode: dict[str, list[str]] = {}
    for mode in MODES:
        retriever = get_retriever_cached(mode)
        output = retriever.search(req.query, top_k=max(req.top_k_per_mode * 3, 10))
        urls: list[str] = []
        for item in output["results"]:
            u = normalize_url(item.get("source", ""))
            if u and u not in urls:
                urls.append(u)
            if len(urls) >= req.top_k_per_mode:
                break
        by_mode[mode] = urls

    return CompareResponse(query=req.query, modes=by_mode)
