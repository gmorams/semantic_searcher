"""
Construccio de l'ontologia formal del domini FIB en RDF/OWL.

Genera `ontology/fib_ontology.ttl` (serialitzacio Turtle) amb:
  - TBox: classes (Titulacio, Grau, Master, Assignatura, Especialitat,
    ConcepteAcademic) i propietats (pertanyA, teEspecialitat,
    dinsEspecialitat, recursCanonic, codi, pesIntencio, patroUrl).
  - ABox: instancies poblades de forma semiautomatica a partir de les dades
    scrapejades (`scraped_data/fib_documents.json`): 4 graus, 4 masters,
    5 especialitats, ~90 assignatures amb nom oficial, i ~18 conceptes
    academics amb etiquetes multilingues (SKOS) i recurs web canonic.

Us:
    python3 ontology/build_ontology.py
"""

import json
import os
import sys

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import OWL, SKOS, XSD

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPED_FILE = os.path.join(BASE_DIR, "scraped_data", "fib_documents.json")
OUTPUT_TTL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fib_ontology.ttl")

FIB = Namespace("https://semanticfib.fib.upc.edu/ontology#")
WEB = "https://www.fib.upc.edu"
GEI_BASE = f"{WEB}/ca/graus/grau-en-enginyeria-informatica"

# ============================================================================
# ABox declarativa: titulacions, especialitats i conceptes academics
# ============================================================================

GRAUS = {
    "GEI": {
        "label": "Grau en Enginyeria Informàtica",
        "alt": ["GEI", "enginyeria informàtica", "ingeniería informática",
                "informatics engineering", "grau d'informàtica"],
        "url": GEI_BASE,
    },
    "GCED": {
        "label": "Grau en Ciència i Enginyeria de Dades",
        "alt": ["GCED", "ciència i enginyeria de dades", "ciencia e ingeniería de datos",
                "data science and engineering"],
        "url": f"{WEB}/ca/graus/grau-en-ciencia-i-enginyeria-de-dades",
    },
    "GIA": {
        "label": "Grau en Intel·ligència Artificial",
        "alt": ["GIA", "grau en intel·ligència artificial", "grado en inteligencia artificial"],
        "url": f"{WEB}/ca/graus/grau-en-intelligencia-artificial",
    },
    "GBIO": {
        "label": "Grau en Bioinformàtica",
        "alt": ["bioinformàtica", "bioinformática", "bioinformatics"],
        "url": f"{WEB}/ca/graus/grau-en-bioinformatica",
    },
}

MASTERS = {
    "MEI": {
        "label": "Màster en Enginyeria Informàtica",
        "alt": ["MEI", "màster en enginyeria informàtica", "máster en ingeniería informática"],
        "url": f"{WEB}/ca/masters/master-en-enginyeria-informatica",
    },
    "MDS": {
        "label": "Màster en Ciència de Dades",
        "alt": ["MDS", "màster en ciència de dades", "máster en ciencia de datos"],
        "url": f"{WEB}/ca/masters/master-en-ciencia-de-dades",
    },
    "MAI": {
        "label": "Màster en Intel·ligència Artificial",
        "alt": ["MAI", "màster en intel·ligència artificial", "máster en inteligencia artificial"],
        "url": f"{WEB}/ca/masters/master-en-intelligencia-artificial",
    },
    "MIRI": {
        "label": "Màster en Innovació i Recerca en Informàtica",
        "alt": ["MIRI", "màster en innovació i recerca en informàtica"],
        "url": f"{WEB}/ca/masters/master-en-innovacio-i-recerca-en-informatica",
    },
}

ESPECIALITATS = {
    "computacio": {
        "label": "Computació",
        "alt": ["computació", "computacion", "computing"],
        "url": f"{GEI_BASE}/pla-destudis/especialitats/computacio",
    },
    "enginyeria-de-computadors": {
        "label": "Enginyeria de Computadors",
        "alt": ["enginyeria de computadors", "ingeniería de computadores", "computer engineering"],
        "url": f"{GEI_BASE}/pla-destudis/especialitats/enginyeria-de-computadors",
    },
    "enginyeria-del-software": {
        "label": "Enginyeria del Software",
        "alt": ["enginyeria del software", "ingeniería del software", "software engineering",
                "especialitat de software"],
        "url": f"{GEI_BASE}/pla-destudis/especialitats/enginyeria-del-software",
    },
    "sistemes-dinformacio": {
        "label": "Sistemes d'Informació",
        "alt": ["sistemes d'informació", "sistemas de información", "information systems"],
        "url": f"{GEI_BASE}/pla-destudis/especialitats/sistemes-dinformacio",
    },
    "tecnologies-de-la-informacio": {
        "label": "Tecnologies de la Informació",
        "alt": ["tecnologies de la informació", "tecnologías de la información",
                "information technologies"],
        "url": f"{GEI_BASE}/pla-destudis/especialitats/tecnologies-de-la-informacio",
    },
}

# Assignatures del GEI agrupades (mateixa font que el scraper)
ASSIGNATURES_PER_GRUP = {
    None: ["F", "FM", "IC", "PRO1", "EC", "M1", "M2", "PRO2",
           "BD", "CI", "EDA", "PE", "SO", "AC", "EEE", "IES", "PROP", "XC", "IDI", "PAR"],
    "computacio": ["A", "G", "IA", "LI", "LP", "TC", "AA", "APA", "CAIM", "CL", "CN", "IO", "SID"],
    "enginyeria-de-computadors": ["AC2", "DSBM", "MP", "PEC", "SO2", "XC2", "CASO", "CPD",
                                  "PAP", "PCA", "PDS", "STR", "VLSI"],
    "enginyeria-del-software": ["AS", "ASW", "DBD", "ER", "GPS", "PES", "CAP", "CBDE",
                                "CSI", "ECSDI", "SIM", "SOAD"],
    "sistemes-dinformacio": ["ADEI", "DSI", "NE", "PSI", "SIO", "ABD", "EDO", "MI", "VPE", "MD"],
    "tecnologies-de-la-informacio": ["ASO", "PI", "PTI", "SI", "SOA", "TXC", "AD", "IM", "SDX", "TCI"],
    "optatives": ["APC", "ASMI", "C", "CCQ", "CDI", "DCS", "EET", "GCS", "GEOC",
                  "LDPE", "PAE", "ROB", "SLDS", "TGA", "VC", "VJ"],
}

# Conceptes academics: etiqueta, sinonims multilingues, recurs canonic,
# pes per al reranking, slugs d'URL per a boosts, i conceptes relacionats.
CONCEPTES = {
    "matricula": {
        "label": "Matrícula",
        "alt": ["matrícula", "matriculació", "automatrícula", "inscripció",
                "matricular-se", "matricularse", "apuntar-se", "apuntar-me",
                "m'apunto", "donar-se d'alta", "matriculación", "inscripción",
                "enrollment"],
        "url": f"{GEI_BASE}/matricula",
        "weight": 0.20, "slugs": ["matricula"],
        "related": ["places lliures", "calendari acadèmic", "normativa acadèmica", "tràmits"],
    },
    "places lliures": {
        "label": "Places lliures",
        "alt": ["places lliures", "places vacants", "vacants", "plazas libres",
                "queden places", "queda lloc", "hi ha places", "hi ha lloc"],
        "url": f"{GEI_BASE}/matricula/places-lliures",
        "weight": 0.25, "slugs": ["places-lliures"],
        "related": ["matrícula"],
    },
    "horaris": {
        "label": "Horaris",
        "alt": ["horari", "horaris", "horario", "horarios", "horari de classes",
                "quan tinc classe", "quina hora", "hora de classe", "aules"],
        "url": f"{GEI_BASE}/horaris",
        "weight": 0.25, "slugs": ["horaris"],
        "related": ["calendari acadèmic", "exàmens"],
    },
    "examens": {
        "label": "Exàmens",
        "alt": ["examen", "exàmens", "examenes", "exámenes", "proves", "parcials",
                "finals", "recuperació", "avaluació", "evaluación"],
        "url": f"{GEI_BASE}/examens",
        "weight": 0.25, "slugs": ["examens"],
        "related": ["horaris", "normativa acadèmica"],
    },
    "professorat": {
        "label": "Professorat",
        "alt": ["professor", "professors", "professora", "professorat", "profesorado",
                "docent", "docents", "tutor", "tutoria", "despatx"],
        "url": f"{GEI_BASE}/professorat",
        "weight": 0.22, "slugs": ["professorat"],
        "related": ["assignatures"],
    },
    "beques": {
        "label": "Beques i ajuts",
        "alt": ["beca", "beques", "ajut", "ajuts", "becas", "ayudas", "scholarship"],
        "url": f"{WEB}/ca/que-necessites/beques-i-ajuts",
        "weight": 0.22, "slugs": ["beques"],
        "related": ["tràmits", "matrícula"],
    },
    "tramits": {
        "label": "Tràmits",
        "alt": ["tràmit", "tràmits", "tramit", "tramits", "trámite", "trámites",
                "gestions", "secretaria", "certificat", "sol·licitud", "instància",
                "convalidació", "reconeixement de crèdits"],
        "url": f"{WEB}/ca/que-necessites/tramits",
        "weight": 0.18, "slugs": ["tramits", "secretaria"],
        "related": ["matrícula", "beques i ajuts", "normativa acadèmica"],
    },
    "treball de fi de grau": {
        "label": "Treball de Fi de Grau",
        "alt": ["treball de fi de grau", "treball final de grau", "TFG",
                "trabajo de fin de grado", "projecte final de carrera"],
        "url": f"{GEI_BASE}/treball-de-fi-de-grau",
        "weight": 0.25, "slugs": ["treball-de-fi-de-grau"],
        "related": ["matrícula", "normativa acadèmica"],
    },
    "mobilitat": {
        "label": "Mobilitat",
        "alt": ["mobilitat", "movilidad", "erasmus", "intercanvi", "exchange",
                "estada internacional", "estudiar fora", "anar fora", "outgoing",
                "incoming", "doble titulació"],
        "url": f"{WEB}/ca/mobilitat",
        "weight": 0.20, "slugs": ["mobilitat", "outgoing", "incoming"],
        "related": ["tràmits", "beques i ajuts"],
    },
    "pla d'estudis": {
        "label": "Pla d'estudis",
        "alt": ["pla d'estudis", "pla destudis", "plan de estudios", "curriculum",
                "itinerari", "crèdits del grau"],
        "url": f"{GEI_BASE}/pla-destudis",
        "weight": 0.15, "slugs": ["pla-destudis"],
        "related": ["especialitats", "assignatures"],
    },
    "especialitats": {
        "label": "Especialitats",
        "alt": ["especialitat", "especialitats", "menció", "mencions", "especialidad",
                "especialidades", "especialización", "specialization"],
        "url": f"{GEI_BASE}/pla-destudis/especialitats",
        "weight": 0.22, "slugs": ["especialitats"],
        "related": ["pla d'estudis"],
    },
    "normativa academica": {
        "label": "Normativa acadèmica",
        "alt": ["normativa", "normatives", "normativa acadèmica", "normativa académica",
                "permanència", "rendiment mínim", "reglament", "convocatòria",
                "convocatòries", "presentar-se a una assignatura"],
        "url": f"{GEI_BASE}/normativa-academica",
        "weight": 0.20, "slugs": ["normativa"],
        "related": ["matrícula", "exàmens"],
    },
    "calendari academic": {
        "label": "Calendari acadèmic",
        "alt": ["calendari", "calendaris", "calendari acadèmic", "calendario académico",
                "dies lectius", "festius", "inici de curs"],
        "url": f"{WEB}/ca/que-necessites/calendaris-academics",
        "weight": 0.20, "slugs": ["calendaris-academics", "calendari"],
        "related": ["horaris", "matrícula"],
    },
    "practiques en empresa": {
        "label": "Pràctiques en empresa",
        "alt": ["pràctiques", "practiques", "prácticas", "pràctiques en empresa",
                "conveni", "convenis", "conveni de cooperació educativa", "internship"],
        "url": f"{WEB}/ca/empresa/practiques-en-empresa",
        "weight": 0.22, "slugs": ["practiques-en-empresa"],
        "related": ["borsa de treball"],
    },
    "borsa de treball": {
        "label": "Borsa de treball",
        "alt": ["borsa de treball", "bolsa de trabajo", "ofertes de feina",
                "ofertas de trabajo", "buscar feina", "treballar", "feina"],
        "url": f"{WEB}/ca/empresa/borsa-de-treball",
        "weight": 0.20, "slugs": ["borsa-de-treball"],
        "related": ["pràctiques en empresa"],
    },
    "nota de tall": {
        "label": "Nota de tall",
        "alt": ["nota de tall", "nota de corte", "nota d'accés", "nota d'admissió"],
        "url": GEI_BASE,
        "weight": 0.15, "slugs": [],
        "related": ["matrícula"],
    },
    "contacte": {
        "label": "Contacte",
        "alt": ["contacte", "contacto", "telèfon", "adreça", "on és la facultat",
                "email de secretaria"],
        "url": f"{WEB}/ca/contacte",
        "weight": 0.15, "slugs": ["contacte"],
        "related": ["tràmits"],
    },
    "la facultat": {
        "label": "La FIB",
        "alt": ["la fib", "la facultat", "facultat d'informàtica",
                "facultad de informática", "què és la fib"],
        "url": f"{WEB}/ca/la-fib",
        "weight": 0.18, "slugs": ["la-fib"],
        "related": ["contacte"],
    },
    "assignatures": {
        "label": "Assignatures",
        "alt": ["assignatura", "assignatures", "asignatura", "asignaturas",
                "matèria", "matèries", "temari", "guia docent"],
        "url": f"{GEI_BASE}/pla-destudis/assignatures",
        "weight": 0.10, "slugs": ["assignatures"],
        "related": ["pla d'estudis", "professorat"],
    },
}


def _slugify(text):
    import unicodedata
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def _load_course_names():
    """Extreu el nom oficial de cada assignatura de les dades scrapejades."""
    names = {}
    if not os.path.exists(SCRAPED_FILE):
        return names
    with open(SCRAPED_FILE, "r", encoding="utf-8") as f:
        documents = json.load(f)
    for doc in documents:
        url = doc.get("url", "")
        if "/pla-destudis/assignatures/" in url:
            code = url.rstrip("/").split("/")[-1]
            title = (doc.get("title") or "").split(" - ")[0].strip()
            if code and title and code not in names:
                names[code] = title
    return names


def build_graph():
    g = Graph()
    g.bind("fib", FIB)
    g.bind("skos", SKOS)
    g.bind("owl", OWL)

    # ------------------------------------------------------------------
    # TBox: classes
    # ------------------------------------------------------------------
    classes = {
        "EntitatAcademica": ("Entitat acadèmica", None),
        "Titulacio": ("Titulació", "EntitatAcademica"),
        "Grau": ("Grau", "Titulacio"),
        "Master": ("Màster", "Titulacio"),
        "Assignatura": ("Assignatura", "EntitatAcademica"),
        "Especialitat": ("Especialitat", "EntitatAcademica"),
        "ConcepteAcademic": ("Concepte acadèmic", "EntitatAcademica"),
    }
    for name, (label, parent) in classes.items():
        cls = FIB[name]
        g.add((cls, RDF.type, OWL.Class))
        g.add((cls, RDFS.label, Literal(label, lang="ca")))
        if parent:
            g.add((cls, RDFS.subClassOf, FIB[parent]))

    # ------------------------------------------------------------------
    # TBox: propietats
    # ------------------------------------------------------------------
    object_props = {
        "pertanyA": ("pertany a", "Assignatura", "Titulacio"),
        "teEspecialitat": ("té especialitat", "Grau", "Especialitat"),
        "dinsEspecialitat": ("dins l'especialitat", "Assignatura", "Especialitat"),
    }
    for name, (label, dom, rng) in object_props.items():
        p = FIB[name]
        g.add((p, RDF.type, OWL.ObjectProperty))
        g.add((p, RDFS.label, Literal(label, lang="ca")))
        g.add((p, RDFS.domain, FIB[dom]))
        g.add((p, RDFS.range, FIB[rng]))

    data_props = {
        "codi": ("codi", XSD.string),
        "recursCanonic": ("recurs web canònic", XSD.anyURI),
        "pesIntencio": ("pes d'intenció per al reranking", XSD.float),
        "patroUrl": ("patró d'URL per al reranking", XSD.string),
    }
    for name, (label, rng) in data_props.items():
        p = FIB[name]
        g.add((p, RDF.type, OWL.DatatypeProperty))
        g.add((p, RDFS.label, Literal(label, lang="ca")))
        g.add((p, RDFS.range, rng))

    # ------------------------------------------------------------------
    # ABox: titulacions
    # ------------------------------------------------------------------
    for acronym, data in GRAUS.items():
        uri = FIB[f"grau-{_slugify(data['label'])}"]
        g.add((uri, RDF.type, FIB.Grau))
        g.add((uri, SKOS.prefLabel, Literal(data["label"], lang="ca")))
        g.add((uri, FIB.codi, Literal(acronym)))
        g.add((uri, FIB.recursCanonic, Literal(data["url"], datatype=XSD.anyURI)))
        for alt in data["alt"]:
            g.add((uri, SKOS.altLabel, Literal(alt, lang="ca")))

    for acronym, data in MASTERS.items():
        uri = FIB[f"master-{_slugify(data['label'])}"]
        g.add((uri, RDF.type, FIB.Master))
        g.add((uri, SKOS.prefLabel, Literal(data["label"], lang="ca")))
        g.add((uri, FIB.codi, Literal(acronym)))
        g.add((uri, FIB.recursCanonic, Literal(data["url"], datatype=XSD.anyURI)))
        for alt in data["alt"]:
            g.add((uri, SKOS.altLabel, Literal(alt, lang="ca")))

    # ------------------------------------------------------------------
    # ABox: especialitats del GEI
    # ------------------------------------------------------------------
    gei_uri = FIB[f"grau-{_slugify(GRAUS['GEI']['label'])}"]
    esp_uris = {}
    for slug, data in ESPECIALITATS.items():
        uri = FIB[f"especialitat-{slug}"]
        esp_uris[slug] = uri
        g.add((uri, RDF.type, FIB.Especialitat))
        g.add((uri, SKOS.prefLabel, Literal(data["label"], lang="ca")))
        g.add((uri, FIB.recursCanonic, Literal(data["url"], datatype=XSD.anyURI)))
        g.add((gei_uri, FIB.teEspecialitat, uri))
        for alt in data["alt"]:
            g.add((uri, SKOS.altLabel, Literal(alt, lang="ca")))

    # ------------------------------------------------------------------
    # ABox: assignatures (poblades amb noms reals del scraping)
    # ------------------------------------------------------------------
    course_names = _load_course_names()
    for group, codes in ASSIGNATURES_PER_GRUP.items():
        for code in codes:
            uri = FIB[f"assignatura-{code}"]
            g.add((uri, RDF.type, FIB.Assignatura))
            g.add((uri, FIB.codi, Literal(code)))
            g.add((uri, FIB.pertanyA, gei_uri))
            name = course_names.get(code)
            g.add((uri, SKOS.prefLabel, Literal(name or code, lang="ca")))
            if name:
                g.add((uri, SKOS.altLabel, Literal(code)))
            url = f"{GEI_BASE}/pla-destudis/assignatures/{code}"
            g.add((uri, FIB.recursCanonic, Literal(url, datatype=XSD.anyURI)))
            if group in esp_uris:
                g.add((uri, FIB.dinsEspecialitat, esp_uris[group]))

    # ------------------------------------------------------------------
    # ABox: conceptes academics
    # ------------------------------------------------------------------
    concept_uris = {}
    for key, data in CONCEPTES.items():
        uri = FIB[f"concepte-{_slugify(key)}"]
        concept_uris[data["label"].lower()] = uri
        g.add((uri, RDF.type, FIB.ConcepteAcademic))
        g.add((uri, SKOS.prefLabel, Literal(data["label"], lang="ca")))
        g.add((uri, FIB.recursCanonic, Literal(data["url"], datatype=XSD.anyURI)))
        g.add((uri, FIB.pesIntencio, Literal(data["weight"], datatype=XSD.float)))
        for alt in data["alt"]:
            g.add((uri, SKOS.altLabel, Literal(alt, lang="ca")))
        for slug in data["slugs"]:
            g.add((uri, FIB.patroUrl, Literal(slug)))

    # Relacions skos:related entre conceptes
    for key, data in CONCEPTES.items():
        uri = FIB[f"concepte-{_slugify(key)}"]
        for rel_label in data.get("related", []):
            rel_uri = concept_uris.get(rel_label.lower())
            if rel_uri is not None:
                g.add((uri, SKOS.related, rel_uri))
                g.add((rel_uri, SKOS.related, uri))

    return g


def main():
    g = build_graph()
    g.serialize(destination=OUTPUT_TTL, format="turtle")
    n_classes = len(list(g.subjects(RDF.type, OWL.Class)))
    n_instances = len(set(g.subjects(FIB.recursCanonic, None)))
    print(f"Ontologia generada: {OUTPUT_TTL}")
    print(f"  Triples:    {len(g)}")
    print(f"  Classes:    {n_classes}")
    print(f"  Instancies: {n_instances}")


if __name__ == "__main__":
    sys.exit(main())
