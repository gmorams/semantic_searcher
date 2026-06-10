"""
Ontologia simple del domini de la FIB (Facultat d'Informatica de Barcelona).

Aquesta ontologia estructura el coneixement del domini universitari
i s'utilitza per enriquir les consultes amb relacions conceptuals,
millorant la recuperacio d'informacio respecte a una cerca purament vectorial.

Es un component clau del TFG: demostra com el coneixement estructurat
(ontologies) pot col-laborar amb els LLMs per a una cerca semantica superior.
"""

# ============================================================================
# ONTOLOGIA: Graf de conceptes i les seves relacions semantiques
# ============================================================================

FIB_ONTOLOGY = {
    # --- Domini Academic ---
    "matricula": {
        "sinonims": ["matriculacio", "inscripcio", "enrollment"],
        "relacionats": ["prematricula", "modificacio de matricula", "anul-lacio",
                        "credits", "taxes", "terminis", "convocatoria", "automatricula"],
        "subtipus": ["matricula ordinaria", "matricula extraordinaria"],
        "propietats": ["termini", "preu", "credits"],
    },
    "assignatura": {
        "sinonims": ["materia", "curs", "course", "asignatura"],
        "relacionats": ["prerequisit", "credits", "professor", "horari", "guia docent",
                        "avaluacio", "examen", "practiques", "laboratori", "seminari"],
        "subtipus": ["obligatoria", "optativa", "projecte", "treball final de grau"],
        "propietats": ["codi", "credits", "semestre", "idioma", "departament"],
    },
    "grau": {
        "sinonims": ["carrera", "estudis", "degree", "grado"],
        "relacionats": ["especialitat", "pla d'estudis", "titulacio", "GEI",
                        "grau en enginyeria informatica"],
        "subtipus": ["grau", "master", "doctorat"],
        "propietats": ["credits totals", "durada", "especialitats"],
    },
    "especialitat": {
        "sinonims": ["mencio", "especialitzacio", "specialization"],
        "relacionats": ["computacio", "enginyeria del software", "sistemes d'informacio",
                        "tecnologies de la informacio", "enginyeria de computadors"],
        "subtipus": [],
        "propietats": ["credits", "assignatures"],
    },
    "professor": {
        "sinonims": ["docent", "professorat", "tutor", "profesor"],
        "relacionats": ["departament", "despatx", "tutoria", "horari d'atencio",
                        "investigacio"],
        "propietats": ["nom", "email", "departament"],
    },
    "tramit": {
        "sinonims": ["procediment", "gestio", "tramite", "proces"],
        "relacionats": ["secretaria", "documentacio", "termini", "formulari",
                        "certificat", "convalidacio", "trasllat d'expedient"],
        "subtipus": ["tramit academic", "tramit administratiu"],
        "propietats": ["termini", "requisits", "documentacio"],
    },

    # --- Domini Tecnic (Cerca Semantica) ---
    "ontologia": {
        "sinonims": ["knowledge graph", "graf de coneixement", "ontology"],
        "relacionats": ["concepte", "relacio", "classe", "instancia", "propietat",
                        "RDF", "OWL", "SPARQL", "taxonomia", "semantica",
                        "representacio del coneixement"],
        "subtipus": ["ontologia de domini", "ontologia superior"],
    },
    "LLM": {
        "sinonims": ["model de llenguatge", "language model", "GPT",
                     "model d'intelligencia artificial", "large language model"],
        "relacionats": ["embedding", "prompt", "RAG", "fine-tuning", "tokenitzacio",
                        "generacio de text", "comprensio del llenguatge natural",
                        "transformer", "atencio"],
        "subtipus": ["GPT-4", "Claude", "Llama"],
    },
    "cerca semantica": {
        "sinonims": ["busqueda semantica", "semantic search", "cerca intel-ligent"],
        "relacionats": ["embedding", "similitud del cosinus", "vector", "indexacio",
                        "recuperacio d'informacio", "BM25", "cerca lexica",
                        "cerca vectorial", "TF-IDF"],
        "subtipus": ["cerca vectorial", "cerca hibrida", "cerca lexica"],
    },
    "embedding": {
        "sinonims": ["representacio vectorial", "vector", "vector dens"],
        "relacionats": ["similitud", "espai vectorial", "model d'embeddings",
                        "sentence-transformers", "cosine similarity",
                        "dimensionalitat", "espai latent"],
        "subtipus": ["word embedding", "sentence embedding", "document embedding"],
    },
    "RAG": {
        "sinonims": ["Retrieval Augmented Generation",
                     "generacio augmentada per recuperacio"],
        "relacionats": ["recuperacio", "generacio", "context", "chunks",
                        "base de coneixement", "vector store", "prompt engineering",
                        "grounding"],
        "subtipus": [],
    },
}

# ============================================================================
# RELACIONS: Arestes del graf ontologic
# ============================================================================

RELATIONS = [
    ("assignatura", "te_prerequisit", "assignatura"),
    ("professor", "imparteix", "assignatura"),
    ("assignatura", "pertany_a", "grau"),
    ("grau", "te_especialitat", "especialitat"),
    ("assignatura", "requereix", "matricula"),
    ("tramit", "relacionat_amb", "matricula"),
    ("ontologia", "millora", "cerca semantica"),
    ("LLM", "genera", "embedding"),
    ("RAG", "utilitza", "LLM"),
    ("RAG", "utilitza", "cerca semantica"),
    ("embedding", "permet", "cerca semantica"),
    ("ontologia", "estructura", "coneixement"),
    ("LLM", "comprèn", "llenguatge natural"),
]


# ============================================================================
# FUNCIONS D'ENRIQUIMENT DE CONSULTES
# ============================================================================

def enrich_query(query: str) -> str:
    """
    Enriqueix una consulta amb termes relacionats de l'ontologia.

    Aquesta es la funcio clau que demostra la col-laboracio
    ontologia-LLM: abans de fer la cerca vectorial, expandim
    la consulta amb coneixement estructurat.

    Args:
        query: La consulta original de l'usuari.

    Returns:
        La consulta enriquida amb termes ontologics addicionals.
    """
    query_lower = query.lower()
    additional_terms = set()
    matched_concepts = []

    for concept, data in FIB_ONTOLOGY.items():
        all_terms = [concept] + data.get("sinonims", [])

        for term in all_terms:
            if term.lower() in query_lower:
                matched_concepts.append(concept)
                for related in data.get("relacionats", []):
                    additional_terms.add(related)
                for synonym in data.get("sinonims", []):
                    additional_terms.add(synonym)
                for subtype in data.get("subtipus", []):
                    if subtype:
                        additional_terms.add(subtype)
                break

    # Afegir termes de relacions
    for subj, rel, obj in RELATIONS:
        if subj in matched_concepts or obj in matched_concepts:
            additional_terms.add(subj)
            additional_terms.add(obj)

    if additional_terms:
        # Eliminar termes massa generics que generen soroll
        generic_terms = {"grau", "master", "doctorat", "degree", "grado",
                         "carrera", "estudis", "course", "coneixement",
                         "llenguatge natural"}
        additional_terms -= generic_terms
        # Eliminar termes que ja apareixen a la consulta
        additional_terms = {t for t in additional_terms if t.lower() not in query_lower}
        # Limitar a 8 termes per no saturar la consulta
        terms_list = sorted(additional_terms)[:8]
        if terms_list:
            enrichment = " ".join(terms_list)
            return f"{query} {enrichment}"

    return query


def get_ontology_context(query: str) -> str:
    """
    Retorna context estructurat de l'ontologia per incloure al prompt del LLM.

    Args:
        query: La consulta de l'usuari.

    Returns:
        Text formatat amb el context ontologic rellevant.
    """
    query_lower = query.lower()
    context_parts = []

    for concept, data in FIB_ONTOLOGY.items():
        all_terms = [concept] + data.get("sinonims", [])

        for term in all_terms:
            if term.lower() in query_lower:
                context_parts.append(f"Concepte: {concept}")
                if data.get("sinonims"):
                    context_parts.append(f"  Sinonims: {', '.join(data['sinonims'][:5])}")
                if data.get("relacionats"):
                    context_parts.append(f"  Relacionats: {', '.join(data['relacionats'][:8])}")
                if data.get("subtipus"):
                    subs = [s for s in data["subtipus"] if s]
                    if subs:
                        context_parts.append(f"  Subtipus: {', '.join(subs)}")

                # Relacions on participa
                rels = [(s, r, o) for s, r, o in RELATIONS
                        if s == concept or o == concept]
                if rels:
                    rel_strs = [f"{s} --{r}--> {o}" for s, r, o in rels]
                    context_parts.append(f"  Relacions: {'; '.join(rel_strs)}")
                break

    return "\n".join(context_parts) if context_parts else ""


def get_all_concepts() -> list:
    """Retorna la llista de tots els conceptes de l'ontologia."""
    return list(FIB_ONTOLOGY.keys())
