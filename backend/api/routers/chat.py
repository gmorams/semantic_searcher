from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage

from ..deps import get_rag_chain
from ..schemas import (
    AskAllRequest,
    AskAllResponse,
    AskRequest,
    AskResponse,
    RetrievedDoc,
)

router = APIRouter()


def _history_to_messages(history):
    out = []
    for msg in history:
        if msg.role == "user":
            out.append(HumanMessage(content=msg.content))
        else:
            out.append(AIMessage(content=msg.content))
    return out


def _build_ask_response(req_question: str, result: dict) -> AskResponse:
    docs = [
        RetrievedDoc(
            rank=d.get("rank", 0),
            title=d.get("title", ""),
            section=d.get("section", ""),
            source=d.get("source", ""),
            preview=d.get("preview", ""),
            score=float(d.get("score", 0.0)),
            similarity=float(d.get("similarity", 0.0)),
            retrieval_source=d.get("retrieval_source", ""),
            boosts=list(d.get("boosts", [])),
        )
        for d in result.get("retrieved_docs", [])
    ]
    return AskResponse(
        answer=result["answer"],
        mode=result["mode"],
        sources=result["sources"],
        search_question=result.get("search_question", req_question),
        enriched_query=result.get("enriched_query", req_question),
        ontology_context=result.get("ontology_context") or None,
        api_context=result.get("api_context") or None,
        entities=result.get("entities", []),
        num_docs_retrieved=result.get("num_docs_retrieved", len(docs)),
        retrieved_docs=docs,
    )


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    try:
        chain = get_rag_chain(req.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result = chain.ask(req.question, _history_to_messages(req.history))
    return _build_ask_response(req.question, result)


@router.post("/ask-all", response_model=AskAllResponse)
def ask_all(req: AskAllRequest) -> AskAllResponse:
    """Lanza la misma pregunta con las 5 estrategias en paralelo."""
    from retrieval import MODES

    history = _history_to_messages(req.history)

    def _run_one(mode: str):
        try:
            chain = get_rag_chain(mode)
            result = chain.ask(req.question, history)
            return mode, _build_ask_response(req.question, result), None
        except Exception as exc:  # pragma: no cover
            return mode, None, f"{type(exc).__name__}: {exc}"

    responses: dict[str, AskResponse] = {}
    errors: dict[str, str] = {}
    # cada chain tiene su propio cliente LLM; las llamadas son independientes
    with ThreadPoolExecutor(max_workers=len(MODES)) as pool:
        for mode, resp, err in pool.map(_run_one, MODES):
            if err is not None:
                errors[mode] = err
            else:
                responses[mode] = resp

    return AskAllResponse(question=req.question, responses=responses, errors=errors)
