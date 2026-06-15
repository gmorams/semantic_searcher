"""
API de consulta sobre l'ontologia formal del domini FIB (RDF/OWL).

L'ontologia es construeix amb `build_ontology.py` i es persisteix a
`fib_ontology.ttl`. Aquest modul la carrega amb rdflib i exposa les
operacions que utilitza el pipeline de cerca:

  - match_concepts(query):   deteccio de conceptes per matching normalitzat
                             (sense accents, word boundaries) sobre les
                             etiquetes SKOS (prefLabel + altLabel).
  - enrich_query(query):     expansio de la consulta amb sinonims i conceptes
                             relacionats (via SPARQL sobre skos:related).
  - intent_resources(query): recursos web canonics associats als conceptes
                             detectats, amb el seu pes d'intencio (per al
                             reranking controlat).
  - get_ontology_context():  context estructurat per al prompt del LLM.
"""

import os
import re
import unicodedata

from rdflib import Graph, Namespace, RDF
from rdflib.namespace import OWL, SKOS

from utils import SingletonMeta

FIB = Namespace("https://semanticfib.fib.upc.edu/ontology#")
TTL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fib_ontology.ttl")


def normalize(text):
    """Minuscules + sense accents/diacritics (apostrofs i punts volats fora)."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().replace("·", "").replace("'", " ").replace("’", " ")


class FIBOntology(metaclass=SingletonMeta):
    """Wrapper de l'ontologia RDF amb indexs de matching en memoria."""

    def __init__(self):
        if not os.path.exists(TTL_PATH):
            from ontology.build_ontology import build_graph
            graph = build_graph()
            graph.serialize(destination=TTL_PATH, format="turtle")

        self.graph = Graph()
        self.graph.parse(TTL_PATH, format="turtle")
        self.graph.bind("fib", FIB)
        self.graph.bind("skos", SKOS)

        self._build_indexes()

    # ------------------------------------------------------------------
    # Indexs
    # ------------------------------------------------------------------

    def _build_indexes(self):
        """Construeix indexs en memoria a partir del graf RDF."""
        self.concepts = {}      # uri -> dict del concepte/instancia
        self._term_index = []   # (terme normalitzat, regex, uri)

        for uri in set(self.graph.subjects(FIB.recursCanonic, None)):
            rdf_types = set(self.graph.objects(uri, RDF.type))
            if FIB.Assignatura in rdf_types:
                ctype = "Assignatura"
            elif FIB.Grau in rdf_types:
                ctype = "Grau"
            elif FIB.Master in rdf_types:
                ctype = "Màster"
            elif FIB.Especialitat in rdf_types:
                ctype = "Especialitat"
            else:
                ctype = "Concepte acadèmic"

            pref = str(next(self.graph.objects(uri, SKOS.prefLabel), ""))
            alts = [str(o) for o in self.graph.objects(uri, SKOS.altLabel)]
            url = str(next(self.graph.objects(uri, FIB.recursCanonic), ""))
            weight = next(self.graph.objects(uri, FIB.pesIntencio), None)
            slugs = [str(o) for o in self.graph.objects(uri, FIB.patroUrl)]
            code = str(next(self.graph.objects(uri, FIB.codi), ""))

            default_weight = 0.30 if ctype == "Assignatura" else 0.15
            self.concepts[uri] = {
                "uri": uri,
                "type": ctype,
                "label": pref,
                "synonyms": alts,
                "url": url,
                "weight": float(weight) if weight is not None else default_weight,
                "slugs": slugs,
                "code": code,
            }

            # Les assignatures: els CODIS es resolen al entity linker (matching
            # sensible a majuscules); aqui nomes s'indexa el nom oficial complet
            # ("Bases de Dades", "Xarxes de Computadors"...).
            if ctype == "Assignatura":
                if pref and pref != code:
                    name_norm = normalize(pref)
                    if len(name_norm) >= 8:
                        pattern = re.compile(r"\b" + re.escape(name_norm) + r"\b")
                        self._term_index.append((name_norm, pattern, uri))
                continue

            for term in [pref] + alts:
                term_norm = normalize(term)
                # Sigles curtes (GEI, MAI...) tambe van al entity linker
                if len(term_norm) < 4 and term_norm.isalpha() and term.isupper():
                    continue
                if len(term_norm) < 3:
                    continue
                pattern = re.compile(r"\b" + re.escape(term_norm) + r"\b")
                self._term_index.append((term_norm, pattern, uri))

        # Termes mes llargs primer: si matcha "treball de fi de grau" no cal "grau"
        self._term_index.sort(key=lambda t: -len(t[0]))

    # ------------------------------------------------------------------
    # Matching de conceptes
    # ------------------------------------------------------------------

    def match_concepts(self, query):
        """Retorna els conceptes de l'ontologia detectats a la consulta."""
        query_norm = normalize(query)
        matched = {}
        covered = set()
        for term_norm, pattern, uri in self._term_index:
            m = pattern.search(query_norm)
            if not m:
                continue
            span = set(range(m.start(), m.end()))
            # Evitar que un terme contingut dins un altre ja matchat compti
            if span & covered:
                continue
            covered |= span
            if uri not in matched:
                concept = dict(self.concepts[uri])
                concept["matched_term"] = term_norm
                matched[uri] = concept
        return list(matched.values())

    # ------------------------------------------------------------------
    # Expansio de consulta (SPARQL sobre skos:related)
    # ------------------------------------------------------------------

    def expansion_terms(self, query, max_terms=8):
        """Sinonims + etiquetes de conceptes relacionats per expandir la query."""
        query_norm = normalize(query)
        terms = []

        for concept in self.match_concepts(query):
            for syn in concept["synonyms"]:
                if normalize(syn) not in query_norm and syn not in terms:
                    terms.append(syn)

            sparql = """
                SELECT DISTINCT ?relLabel WHERE {
                    ?uri skos:related ?rel .
                    ?rel skos:prefLabel ?relLabel .
                }
            """
            for row in self.graph.query(sparql, initBindings={"uri": concept["uri"]}):
                label = str(row.relLabel)
                if normalize(label) not in query_norm and label not in terms:
                    terms.append(label)

        return terms[:max_terms]

    def enrich_query(self, query):
        """Consulta original + termes d'expansio ontologica."""
        terms = self.expansion_terms(query)
        if terms:
            return f"{query} {' '.join(terms)}"
        return query

    # ------------------------------------------------------------------
    # Recursos i regles per al retriever controlat
    # ------------------------------------------------------------------

    def intent_resources(self, query):
        """[(url, pes, etiqueta)] dels recursos canonics dels conceptes detectats."""
        resources = []
        seen = set()
        for concept in self.match_concepts(query):
            url = concept["url"]
            if url and url not in seen:
                seen.add(url)
                resources.append((url, concept["weight"], concept["label"]))
        return resources

    def boost_rules(self, query):
        """[(slug, pes, etiqueta)] per a boosts parcials per pattern d'URL."""
        rules = []
        for concept in self.match_concepts(query):
            for slug in concept["slugs"]:
                rules.append((slug, concept["weight"], concept["label"]))
        return rules

    def matched_degrees(self, query):
        """Titulacions (graus/masters) detectades, per a l'scoping del reranking."""
        return [c for c in self.match_concepts(query) if c["type"] in ("Grau", "Màster")]

    def degree_urls(self):
        """URLs base de totes les titulacions (per a penalitzacions de scoping)."""
        return {c["url"]: c for c in self.concepts.values() if c["type"] in ("Grau", "Màster")}

    def course_index(self):
        """codi -> dades de l'assignatura (per al entity linker)."""
        return {c["code"]: c for c in self.concepts.values()
                if c["type"] == "Assignatura" and c["code"]}

    def acronym_index(self):
        """sigla -> dades de la titulacio (per al entity linker)."""
        return {c["code"]: c for c in self.concepts.values()
                if c["type"] in ("Grau", "Màster") and c["code"]}

    # ------------------------------------------------------------------
    # Context per al prompt del LLM
    # ------------------------------------------------------------------

    def ontology_context(self, query):
        """Text estructurat amb el coneixement ontologic rellevant per al LLM."""
        parts = []
        for concept in self.match_concepts(query):
            parts.append(f"Concepte: {concept['label']} ({concept['type']})")
            if concept["synonyms"]:
                parts.append(f"  Sinonims: {', '.join(concept['synonyms'][:5])}")
            if concept["url"]:
                parts.append(f"  Pagina oficial: {concept['url']}")

            sparql = """
                SELECT DISTINCT ?relLabel WHERE {
                    ?uri skos:related ?rel .
                    ?rel skos:prefLabel ?relLabel .
                }
            """
            related = [str(r.relLabel) for r in
                       self.graph.query(sparql, initBindings={"uri": concept["uri"]})]
            if related:
                parts.append(f"  Relacionats: {', '.join(related)}")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Estadistiques i exploracio (UI)
    # ------------------------------------------------------------------

    def stats(self):
        n_classes = len(list(self.graph.subjects(RDF.type, OWL.Class)))
        by_type = {}
        for c in self.concepts.values():
            by_type[c["type"]] = by_type.get(c["type"], 0) + 1
        return {
            "triples": len(self.graph),
            "classes": n_classes,
            "instances": len(self.concepts),
            "by_type": by_type,
        }

    def concepts_by_type(self):
        grouped = {}
        for c in sorted(self.concepts.values(), key=lambda x: x["label"]):
            grouped.setdefault(c["type"], []).append(c)
        return grouped

    def concept_details(self, label):
        for c in self.concepts.values():
            if c["label"] == label:
                details = dict(c)
                sparql = """
                    SELECT DISTINCT ?relLabel WHERE {
                        ?uri skos:related ?rel .
                        ?rel skos:prefLabel ?relLabel .
                    }
                """
                details["related"] = [str(r.relLabel) for r in
                                      self.graph.query(sparql, initBindings={"uri": c["uri"]})]
                return details
        return None


# ============================================================================
# Funcions de modul (compatibilitat amb el codi existent)
# ============================================================================

def get_ontology():
    return FIBOntology()


def enrich_query(query):
    return get_ontology().enrich_query(query)


def get_ontology_context(query):
    return get_ontology().ontology_context(query)


def get_all_concepts():
    return sorted(c["label"] for c in get_ontology().concepts.values())
