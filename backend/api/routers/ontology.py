from fastapi import APIRouter, HTTPException

from ..deps import get_ontology_singleton
from ..schemas import OntologyClass, OntologyConcept

router = APIRouter()


@router.get("/ontology/classes", response_model=list[OntologyClass])
def classes() -> list[OntologyClass]:
    ont = get_ontology_singleton()
    grouped = ont.concepts_by_type()
    return [OntologyClass(name=k, instance_count=len(v)) for k, v in grouped.items()]


@router.get("/ontology/instances", response_model=list[OntologyConcept])
def instances(cls: str | None = None) -> list[OntologyConcept]:
    ont = get_ontology_singleton()
    grouped = ont.concepts_by_type()
    target = grouped.get(cls, []) if cls else [c for v in grouped.values() for c in v]
    return [
        OntologyConcept(
            label=c["label"],
            type=c["type"],
            code=c.get("code") or None,
            url=c.get("url") or None,
            synonyms=list(c.get("synonyms", [])),
            related=[],
            weight=float(c["weight"]) if c.get("weight") is not None else None,
        )
        for c in target
    ]


@router.get("/ontology/instance/{label}", response_model=OntologyConcept)
def instance_detail(label: str) -> OntologyConcept:
    ont = get_ontology_singleton()
    details = ont.concept_details(label)
    if not details:
        raise HTTPException(status_code=404, detail=f"Instancia no encontrada: {label}")
    return OntologyConcept(
        label=details["label"],
        type=details["type"],
        code=details.get("code") or None,
        url=details.get("url") or None,
        synonyms=list(details.get("synonyms", [])),
        related=list(details.get("related", [])),
        weight=float(details["weight"]) if details.get("weight") is not None else None,
    )
