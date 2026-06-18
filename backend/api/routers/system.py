from fastapi import APIRouter

from ..deps import get_ontology_singleton, get_vector_store
from ..schemas import HealthResponse, StatsResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="1.0.0")


@router.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    from retrieval import MODES

    store = get_vector_store()
    ont = get_ontology_singleton()
    ont_stats = ont.stats()

    return StatsResponse(
        document_count=store.count(),
        ontology_triples=ont_stats["triples"],
        ontology_instances=ont_stats["instances"],
        ontology_classes=ont_stats["classes"],
        instances_by_type=ont_stats["by_type"],
        available_modes=dict(MODES),
    )


@router.get("/modes", response_model=dict)
def modes() -> dict:
    from retrieval import MODES

    return dict(MODES)
