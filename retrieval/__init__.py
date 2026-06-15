"""Factoria d'estrategies de cerca.

Modes disponibles (coherents amb els experiments de la memoria):
    bm25        Baseline lexic (Okapi BM25)
    dense       Baseline vectorial (embeddings + cosinus)
    ontology    EXP.2a: expansio ontologica naive de la consulta
    controlled  EXP.2b: ontologia + entity linking + reranking controlat
    hybrid      EXP.3: fusio RRF (BM25 + vectorial + controlada)
"""

MODES = {
    "bm25": "Baseline lexic (BM25)",
    "dense": "Baseline vectorial (embeddings)",
    "ontology": "Expansio ontologica naive",
    "controlled": "Ontologia controlada + entity linking",
    "hybrid": "Hibrida (RRF: BM25 + vectorial + controlada)",
}

_instances = {}


def get_retriever(mode):
    """Retorna (i memoritza) el retriever del mode indicat."""
    if mode not in MODES:
        raise ValueError(f"Mode de cerca desconegut: {mode}. Disponibles: {list(MODES)}")

    if mode not in _instances:
        if mode == "bm25":
            from retrieval.bm25 import BM25Retriever
            _instances[mode] = BM25Retriever()
        elif mode == "dense":
            from retrieval.dense import DenseRetriever
            _instances[mode] = DenseRetriever()
        elif mode == "ontology":
            from retrieval.ontology_expansion import OntologyExpansionRetriever
            _instances[mode] = OntologyExpansionRetriever()
        elif mode == "controlled":
            from retrieval.controlled_ontology import ControlledOntologyRetriever
            _instances[mode] = ControlledOntologyRetriever()
        elif mode == "hybrid":
            from retrieval.hybrid_rrf import HybridRRFRetriever
            _instances[mode] = HybridRRFRetriever()

    return _instances[mode]
