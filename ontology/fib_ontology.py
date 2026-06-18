"""
API de consulta sobre la ontología formal del dominio FIB (RDF/OWL).

Carga `fib_ontology.ttl` con rdflib y expone matching de conceptos, expansión
de consulta, recursos canónicos y contexto para el prompt del LLM.
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
    """minúsculas, sin acentos y sin apóstrofos/puntos volados."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().replace("·", "").replace("'", " ").replace("’", " ")


class FIBOntology(metaclass=SingletonMeta):
    """Wrapper de la ontología RDF con índices de matching en memoria."""

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

    def _build_indexes(self):
        self.concepts = {}      # uri -> dict del concepto/instancia
        self._term_index = []   # (término normalizado, regex, uri)

        for uri in set(self.graph.subjects(FIB.recursCanonic, None)):
            rdf_types = set(self.graph.objects(uri, RDF.type))
            # OJO: los literales "Assignatura", "Grau", "Màster" y "Especialitat"
            # los consumen el entity linker y el scoping del retriever — no se
            # pueden renombrar. Las clases nuevas (Tràmit, Programa de mobilitat,
            # Espai físic...) se exponen con su nombre pero a efectos de
            # matching/inyección se comportan como "Concepte acadèmic".
            if FIB.Assignatura in rdf_types:
                ctype = "Assignatura"
            elif FIB.Grau in rdf_types:
                ctype = "Grau"
            elif FIB.Master in rdf_types:
                ctype = "Màster"
            elif FIB.Especialitat in rdf_types:
                ctype = "Especialitat"
            elif FIB.Tramit in rdf_types:
                ctype = "Tràmit"
            elif FIB.ProgramaMobilitat in rdf_types:
                ctype = "Programa de mobilitat"
            elif FIB.UnitatRecerca in rdf_types:
                ctype = "Unitat de recerca"
            elif FIB.EspaiFisic in rdf_types:
                ctype = "Espai físic"
            elif FIB.OrganGovern in rdf_types:
                ctype = "Òrgan de govern"
            elif FIB.ServeiFIB in rdf_types:
                ctype = "Servei de la FIB"
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

            # Asignaturas: los códigos los resuelve el entity linker (matching
            # sensible a mayúsculas). Aquí solo indexamos el nombre oficial
            # completo ("Bases de Dades", "Xarxes de Computadors"...).
            if ctype == "Assignatura":
                if pref and pref != code:
                    name_norm = normalize(pref)
                    if len(name_norm) >= 8:
                        pattern = re.compile(r"\b" + re.escape(name_norm) + r"\b")
                        self._term_index.append((name_norm, pattern, uri))
                continue

            for term in [pref] + alts:
                term_norm = normalize(term)
                # Siglas cortas (GEI, MAI...) también pasan por el entity linker
                if len(term_norm) < 4 and term_norm.isalpha() and term.isupper():
                    continue
                if len(term_norm) < 3:
                    continue
                pattern = re.compile(r"\b" + re.escape(term_norm) + r"\b")
                self._term_index.append((term_norm, pattern, uri))

        # Términos largos primero: si matchea "treball de fi de grau" no hace falta "grau"
        self._term_index.sort(key=lambda t: -len(t[0]))

    def match_concepts(self, query):
        """Conceptos de la ontología detectados en la consulta."""
        query_norm = normalize(query)
        matched = {}
        covered = set()
        for term_norm, pattern, uri in self._term_index:
            m = pattern.search(query_norm)
            if not m:
                continue
            span = set(range(m.start(), m.end()))
            # Si un término ya cubierto contiene a otro, descartamos el contenido
            if span & covered:
                continue
            covered |= span
            if uri not in matched:
                concept = dict(self.concepts[uri])
                concept["matched_term"] = term_norm
                matched[uri] = concept
        return list(matched.values())

    # Expansión de consulta (SPARQL sobre skos:related)

    def expansion_terms(self, query, max_terms=8):
        """Sinónimos + etiquetas de conceptos relacionados."""
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
        terms = self.expansion_terms(query)
        if terms:
            return f"{query} {' '.join(terms)}"
        return query

    # Recursos y reglas para el retriever controlado

    def intent_resources(self, query):
        """[(url, peso, etiqueta)] de los recursos canónicos detectados."""
        resources = []
        seen = set()
        for concept in self.match_concepts(query):
            url = concept["url"]
            if url and url not in seen:
                seen.add(url)
                resources.append((url, concept["weight"], concept["label"]))
        return resources

    def boost_rules(self, query):
        """[(slug, peso, etiqueta)] para boosts parciales por patrón de URL."""
        rules = []
        for concept in self.match_concepts(query):
            for slug in concept["slugs"]:
                rules.append((slug, concept["weight"], concept["label"]))
        return rules

    def matched_degrees(self, query):
        """Titulaciones detectadas (para el scoping del reranking)."""
        return [c for c in self.match_concepts(query) if c["type"] in ("Grau", "Màster")]

    def degree_urls(self):
        """URLs base de todas las titulaciones (para penalizaciones de scoping)."""
        return {c["url"]: c for c in self.concepts.values() if c["type"] in ("Grau", "Màster")}

    def course_index(self):
        """codi -> datos de la asignatura (para el entity linker)."""
        return {c["code"]: c for c in self.concepts.values()
                if c["type"] == "Assignatura" and c["code"]}

    def acronym_index(self):
        """sigla -> datos de la titulación (para el entity linker)."""
        return {c["code"]: c for c in self.concepts.values()
                if c["type"] in ("Grau", "Màster") and c["code"]}

    # Contexto para el prompt del LLM

    def ontology_context(self, query):
        """Texto estructurado con el conocimiento ontológico relevante."""
        parts = []
        for concept in self.match_concepts(query):
            parts.append(f"Concepte: {concept['label']} ({concept['type']})")
            if concept["synonyms"]:
                parts.append(f"  Sinonims: {', '.join(concept['synonyms'][:5])}")
            if concept["url"]:
                parts.append(f"  Pagina oficial: {concept['url']}")

            parent = next(self.graph.objects(concept["uri"], FIB.subconcepteDe), None)
            if parent is not None:
                plabel = next(self.graph.objects(parent, SKOS.prefLabel), None)
                if plabel is not None:
                    parts.append(f"  Forma part de: {plabel}")

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

    # Estadísticas y exploración (UI)

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


# Funciones de módulo (compatibilidad con el código existente)

def get_ontology():
    return FIBOntology()


def enrich_query(query):
    return get_ontology().enrich_query(query)


def get_ontology_context(query):
    return get_ontology().ontology_context(query)


def get_all_concepts():
    return sorted(c["label"] for c in get_ontology().concepts.values())
