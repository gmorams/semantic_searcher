"""
Construcción de la ontología formal del dominio FIB en RDF/OWL.

Genera `ontology/fib_ontology.ttl` poblando TBox (clases y propiedades) y ABox
(titulaciones, especialidades, asignaturas y conceptos académicos) a partir de
los datos scrapeados.
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

# ABox declarativa: titulaciones, especialidades y conceptos

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
        "alt": ["MDS", "màster en ciència de dades", "máster en ciencia de datos",
                "ciència de dades", "ciencia de datos", "data science"],
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

# Asignaturas del GEI agrupadas (misma fuente que el scraper)
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

# Conceptos académicos: etiqueta, sinónimos multilingües, recurso canónico,
# peso de reranking, slugs de URL para boosts y conceptos relacionados.
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
                "incoming", "marxar a l'estranger"],
        "url": f"{WEB}/ca/mobilitat",
        "weight": 0.20, "slugs": ["mobilitat", "outgoing", "incoming"],
        "related": ["tràmits", "beques i ajuts", "dobles titulacions",
                    "programes de mobilitat"],
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

    # Páginas de aterrizaje específicas que antes caían bajo conceptos demasiado
    # genéricos (mobilitat, tramits, la facultat...). Cada una con su URL canónica,
    # clase ontológica propia y, cuando aplica, concepto padre (subconcepteDe).

    # Mobilitat: subpáginas
    "dobles titulacions": {
        "label": "Dobles titulacions",
        "alt": ["doble titulació", "dobles titulacions", "doble titulacio",
                "doble titulación", "dobles titulaciones", "doble grau",
                "doble màster", "double degree", "titulació doble",
                "fer dues titulacions", "centres de doble titulació",
                "universitats de doble titulació"],
        "url": f"{WEB}/ca/mobilitat/dobles-titulacions",
        "weight": 0.35, "slugs": ["dobles-titulacions"],
        "class": "ProgramaMobilitat", "parent": "mobilitat",
        "related": ["mobilitat"],
    },
    "programes de mobilitat": {
        "label": "Programes de mobilitat",
        "alt": ["programes de mobilitat", "programa de mobilitat",
                "programes d'intercanvi", "programa d'intercanvi",
                "programas de movilidad", "exchange programs", "sicue",
                "vulcanus", "unitech", "aliances internacionals"],
        "url": f"{WEB}/ca/mobilitat/aliances-internacionals/programes-de-mobilitat",
        "weight": 0.28,
        "slugs": ["programes-de-mobilitat", "aliances-internacionals"],
        "class": "ProgramaMobilitat", "parent": "mobilitat",
        "related": ["mobilitat", "dobles titulacions"],
    },
    "universitats partner": {
        "label": "Universitats partner",
        "alt": ["universitats partner", "universitats sòcies",
                "universitats de destinació", "partner universities",
                "quines universitats", "on puc anar d'erasmus",
                "destinacions de mobilitat", "universidades de destino"],
        "url": f"{WEB}/ca/mobilitat/aliances-internacionals/universitats-partner",
        "weight": 0.26, "slugs": ["universitats-partner"],
        "class": "ProgramaMobilitat", "parent": "mobilitat",
        "related": ["mobilitat", "programes de mobilitat"],
    },

    # Recerca
    "recerca": {
        "label": "Recerca",
        "alt": ["recerca", "investigació", "investigación", "research"],
        "url": f"{WEB}/ca/recerca",
        "weight": 0.18, "slugs": ["recerca"],
        "related": ["departaments", "grups de recerca"],
    },
    "departaments": {
        "label": "Departaments",
        "alt": ["departament", "departaments", "departamento", "departamentos",
                "department", "quins departaments"],
        "url": f"{WEB}/ca/recerca/departaments",
        "weight": 0.24, "slugs": ["departaments"],
        "class": "UnitatRecerca", "parent": "recerca",
        "related": ["recerca"],
    },
    "grups de recerca": {
        "label": "Grups de recerca",
        "alt": ["grup de recerca", "grups de recerca", "grupo de investigación",
                "grups d'investigació", "research group", "research groups"],
        "url": f"{WEB}/ca/recerca/grups-de-recerca",
        "weight": 0.24, "slugs": ["grups-de-recerca"],
        "class": "UnitatRecerca", "parent": "recerca",
        "related": ["recerca"],
    },
    "centres de recerca": {
        "label": "Centres de recerca",
        "alt": ["centre de recerca", "centres de recerca",
                "centro de investigación", "research center"],
        "url": f"{WEB}/ca/recerca/centres-de-recerca",
        "weight": 0.24, "slugs": ["centres-de-recerca"],
        "class": "UnitatRecerca", "parent": "recerca",
        "related": ["recerca"],
    },
    "inlab": {
        "label": "inLab FIB",
        "alt": ["inlab", "inlab fib", "laboratori d'innovació"],
        "url": f"{WEB}/ca/recerca/inlab-fib",
        "weight": 0.24, "slugs": ["inlab-fib"],
        "class": "UnitatRecerca", "parent": "recerca",
        "related": ["recerca"],
    },

    # Espacios físicos
    "biblioteca": {
        "label": "Biblioteca",
        "alt": ["biblioteca", "biblioteca rector gabriel ferraté", "library",
                "sala d'estudi", "on puc estudiar"],
        "url": f"{WEB}/ca/la-fib/espais/biblioteca-rector-gabriel-ferrate",
        "weight": 0.26, "slugs": ["biblioteca"],
        "class": "EspaiFisic", "parent": "la facultat",
        "related": ["la facultat"],
    },
    "laboratoris": {
        "label": "Laboratoris d'informàtica",
        "alt": ["laboratori", "laboratoris", "laboratorios",
                "laboratoris d'informàtica", "labs", "aules de laboratori"],
        "url": f"{WEB}/ca/la-fib/espais/laboratoris-dinformatica",
        "weight": 0.22, "slugs": ["laboratoris-dinformatica", "laboratoris"],
        "class": "EspaiFisic", "parent": "la facultat",
        "related": ["la facultat"],
    },
    "aules": {
        "label": "Aules docents",
        "alt": ["aules docents", "aula docent", "on són les aules",
                "ubicació de les aules"],
        "url": f"{WEB}/ca/la-fib/espais/aules-docents",
        "weight": 0.20, "slugs": ["aules-docents"],
        "class": "EspaiFisic", "parent": "la facultat",
        "related": ["la facultat", "horaris"],
    },

    # Vida universitaria, gobierno e información institucional
    "associacions": {
        "label": "Associacions d'estudiants",
        "alt": ["associació", "associacions", "asociaciones",
                "associacions d'estudiants", "vida universitària",
                "delegació d'estudiants"],
        "url": f"{WEB}/ca/la-fib/vida-universitaria/associacions",
        "weight": 0.22, "slugs": ["associacions"],
        "class": "ServeiFIB", "parent": "la facultat",
        "related": ["la facultat"],
    },
    "govern": {
        "label": "Govern de la FIB",
        "alt": ["govern", "equip de govern", "equip directiu",
                "junta de facultat", "gobierno", "deganat", "degà",
                "qui dirigeix la fib"],
        "url": f"{WEB}/ca/la-fib/la-facultat/govern",
        "weight": 0.20, "slugs": ["govern"],
        "class": "OrganGovern", "parent": "la facultat",
        "related": ["la facultat"],
    },
    "xifres": {
        "label": "La facultat en xifres",
        "alt": ["xifres", "la facultat en xifres", "estadístiques",
                "dades estadístiques", "cifras", "datos estadísticos"],
        "url": f"{WEB}/ca/la-fib/la-facultat/la-facultat-en-xifres",
        "weight": 0.20, "slugs": ["la-facultat-en-xifres"],
        "class": "ServeiFIB", "parent": "la facultat",
        "related": ["la facultat"],
    },
    "actes academics": {
        "label": "Actes acadèmics",
        "alt": ["acte acadèmic", "actes acadèmics", "graduació",
                "cerimònia de graduació", "acto académico"],
        "url": f"{WEB}/ca/la-fib/la-facultat/actes-academics",
        "weight": 0.18, "slugs": ["actes-academics"],
        "class": "ServeiFIB", "parent": "la facultat",
        "related": ["la facultat"],
    },

    # Trámites específicos (subconcepteDe "tramits")
    "cita previa": {
        "label": "Cita prèvia",
        "alt": ["cita prèvia", "cita previa", "demanar cita",
                "demanar hora", "appointment", "atenció presencial"],
        "url": f"{WEB}/ca/que-necessites/cita-previa",
        "weight": 0.24, "slugs": ["cita-previa"],
        "class": "Tramit", "parent": "tramits",
        "related": ["tràmits", "contacte"],
    },
    "bustia": {
        "label": "Bústia FIB",
        "alt": ["bústia", "bustia", "queixa", "queixes", "suggeriment",
                "reclamació", "quejas", "bústia de queixes"],
        "url": f"{WEB}/ca/que-necessites/bustia-fib",
        "weight": 0.20, "slugs": ["bustia-fib"],
        "class": "ServeiFIB", "parent": "tramits",
        "related": ["tràmits"],
    },
    "reconeixement de credits": {
        "label": "Reconeixement de crèdits",
        "alt": ["reconeixement de crèdits", "reconeixement d'assignatures",
                "reconocimiento de créditos", "convalidar assignatures",
                "convalidació d'assignatures"],
        "url": f"{WEB}/ca/que-necessites/tramits/reconeixement-dassignatures",
        "weight": 0.26, "slugs": ["reconeixement"],
        "class": "Tramit", "parent": "tramits",
        "related": ["tràmits"],
    },
    "canvi de mencio": {
        "label": "Canvi de menció",
        "alt": ["canvi de menció", "canviar d'especialitat",
                "canvi d'especialitat", "cambio de mención",
                "canviar de menció"],
        "url": f"{WEB}/ca/que-necessites/tramits/canvi-de-mencio-gei",
        "weight": 0.26, "slugs": ["canvi-de-mencio"],
        "class": "Tramit", "parent": "tramits",
        "related": ["tràmits", "especialitats"],
    },
    "trasllat expedient": {
        "label": "Trasllat d'expedient",
        "alt": ["trasllat d'expedient", "trasllat", "traslado de expediente",
                "canviar d'universitat"],
        "url": f"{WEB}/ca/que-necessites/tramits/trasllat-dun-expedient",
        "weight": 0.26, "slugs": ["trasllat"],
        "class": "Tramit", "parent": "tramits",
        "related": ["tràmits"],
    },
    "simultaneitat estudis": {
        "label": "Simultaneïtat d'estudis",
        "alt": ["simultaneïtat", "simultaneitat d'estudis",
                "estudiar dues carreres", "simultaneidad de estudios",
                "cursar dos graus alhora"],
        "url": f"{WEB}/ca/que-necessites/tramits/simultaneitat-destudis",
        "weight": 0.26, "slugs": ["simultaneitat"],
        "class": "Tramit", "parent": "tramits",
        "related": ["tràmits"],
    },
    "certificats": {
        "label": "Certificats acadèmics",
        "alt": ["certificat", "certificats", "certificació acadèmica",
                "certificado académico", "demanar un certificat"],
        "url": f"{WEB}/ca/que-necessites/tramits/certificacions-academiques",
        "weight": 0.24, "slugs": ["certificacions"],
        "class": "Tramit", "parent": "tramits",
        "related": ["tràmits"],
    },
    "titol": {
        "label": "Sol·licitud del títol",
        "alt": ["recollir el títol", "demanar el títol", "expedició del títol",
                "obtenir el títol", "recollida del títol",
                "suplement europeu al títol"],
        "url": f"{WEB}/ca/que-necessites/tramits/recollida-del-titol",
        "weight": 0.24, "slugs": ["recollida-del-titol"],
        "class": "Tramit", "parent": "tramits",
        "related": ["tràmits"],
    },
    "baixa matricula": {
        "label": "Renúncia de matrícula",
        "alt": ["renúncia de matrícula", "donar-se de baixa",
                "anul·lar la matrícula", "baixa acadèmica",
                "treure assignatures de la matrícula"],
        "url": f"{WEB}/ca/que-necessites/tramits/renuncia-la-matricula",
        "weight": 0.24, "slugs": ["renuncia"],
        "class": "Tramit", "parent": "tramits",
        "related": ["tràmits", "matrícula"],
    },
}


def _slugify(text):
    import unicodedata
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


SLUG_TO_ACRONYM = {
    "grau-en-enginyeria-informatica": "GEI",
    "grau-en-ciencia-i-enginyeria-de-dades": "GCED",
    "grau-en-intelligencia-artificial": "GIA",
    "grau-en-bioinformatica": "GBIO",
    "master-en-enginyeria-informatica": "MEI",
    "master-en-ciencia-de-dades": "MDS",
    "master-en-intelligencia-artificial": "MAI",
    "master-en-innovacio-i-recerca-en-informatica": "MIRI",
}


def _load_course_names():
    """Nombre oficial de cada asignatura desde los datos scrapeados."""
    return {c["code"]: c["name"] for c in _load_courses_from_scrape().values()}


def _load_courses_from_scrape():
    """code -> {name, url, program_slug, program_acronym, program_type}."""
    courses = {}
    if not os.path.exists(SCRAPED_FILE):
        return courses
    with open(SCRAPED_FILE, "r", encoding="utf-8") as f:
        documents = json.load(f)
    for doc in documents:
        url = doc.get("url", "")
        if "/pla-destudis/assignatures/" not in url:
            continue
        code = url.rstrip("/").split("/")[-1]
        if not code or code == "assignatures":
            continue

        program_slug = None
        program_type = None
        if "/graus/" in url:
            program_slug = url.split("/graus/")[1].split("/")[0]
            program_type = "Grau"
        elif "/masters/" in url:
            program_slug = url.split("/masters/")[1].split("/")[0]
            program_type = "Master"
        else:
            continue

        title = (doc.get("title") or "").split(" - ")[0].strip()
        canonical_url = url.split("#")[0].rstrip("/")
        entry = {
            "code": code,
            "name": title or code,
            "url": canonical_url,
            "program_slug": program_slug,
            "program_acronym": SLUG_TO_ACRONYM.get(program_slug, program_slug),
            "program_type": program_type,
        }
        # En caso de duplicado preferimos la URL más larga/específica
        if code not in courses or len(entry["url"]) >= len(courses[code]["url"]):
            courses[code] = entry
    return courses


def build_graph():
    g = Graph()
    g.bind("fib", FIB)
    g.bind("skos", SKOS)
    g.bind("owl", OWL)

    # TBox: clases
    classes = {
        "EntitatAcademica": ("Entitat acadèmica", None),
        "Titulacio": ("Titulació", "EntitatAcademica"),
        "Grau": ("Grau", "Titulacio"),
        "Master": ("Màster", "Titulacio"),
        "Assignatura": ("Assignatura", "EntitatAcademica"),
        "Especialitat": ("Especialitat", "EntitatAcademica"),
        "ConcepteAcademic": ("Concepte acadèmic", "EntitatAcademica"),
        # Clases nuevas para modelar con más precisión el dominio
        "Tramit": ("Tràmit", "ConcepteAcademic"),
        "ProgramaMobilitat": ("Programa de mobilitat", "ConcepteAcademic"),
        "UnitatRecerca": ("Unitat de recerca", "EntitatAcademica"),
        "EspaiFisic": ("Espai físic", "EntitatAcademica"),
        "ServeiFIB": ("Servei de la FIB", "EntitatAcademica"),
        "OrganGovern": ("Òrgan de govern", "EntitatAcademica"),
    }
    for name, (label, parent) in classes.items():
        cls = FIB[name]
        g.add((cls, RDF.type, OWL.Class))
        g.add((cls, RDFS.label, Literal(label, lang="ca")))
        if parent:
            g.add((cls, RDFS.subClassOf, FIB[parent]))

    # TBox: propiedades
    object_props = {
        "pertanyA": ("pertany a", "Assignatura", "Titulacio"),
        "teEspecialitat": ("té especialitat", "Grau", "Especialitat"),
        "dinsEspecialitat": ("dins l'especialitat", "Assignatura", "Especialitat"),
        # Jerarquía entre conceptos: p.ej. "dobles titulacions" subconcepteDe "mobilitat"
        "subconcepteDe": ("subconcepte de", "ConcepteAcademic", "ConcepteAcademic"),
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

    # ABox: titulaciones
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

    # ABox: especialidades del GEI
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

    # ABox: asignaturas del GEI (lista estática + relación con especialidad)
    course_names = _load_course_names()
    scraped_courses = _load_courses_from_scrape()
    gei_codes = set()
    for group, codes in ASSIGNATURES_PER_GRUP.items():
        for code in codes:
            gei_codes.add(code)
            uri = FIB[f"assignatura-{code}"]
            g.add((uri, RDF.type, FIB.Assignatura))
            g.add((uri, FIB.codi, Literal(code)))
            g.add((uri, FIB.pertanyA, gei_uri))
            name = course_names.get(code) or scraped_courses.get(code, {}).get("name") or code
            g.add((uri, SKOS.prefLabel, Literal(name, lang="ca")))
            if name != code:
                g.add((uri, SKOS.altLabel, Literal(code)))
            url = scraped_courses.get(code, {}).get("url") or f"{GEI_BASE}/pla-destudis/assignatures/{code}"
            g.add((uri, FIB.recursCanonic, Literal(url, datatype=XSD.anyURI)))
            if group in esp_uris:
                g.add((uri, FIB.dinsEspecialitat, esp_uris[group]))

    # ABox: asignaturas del resto de titulaciones (desde el scraping)
    titulacio_uris = {}
    for acronym, data in GRAUS.items():
        titulacio_uris[acronym] = FIB[f"grau-{_slugify(data['label'])}"]
    for acronym, data in MASTERS.items():
        titulacio_uris[acronym] = FIB[f"master-{_slugify(data['label'])}"]

    n_extra = 0
    for code, info in sorted(scraped_courses.items()):
        if code in gei_codes:
            continue
        tit_uri = titulacio_uris.get(info["program_acronym"])
        if tit_uri is None:
            continue
        uri = FIB[f"assignatura-{code}"]
        g.add((uri, RDF.type, FIB.Assignatura))
        g.add((uri, FIB.codi, Literal(code)))
        g.add((uri, FIB.pertanyA, tit_uri))
        name = info["name"] or code
        g.add((uri, SKOS.prefLabel, Literal(name, lang="ca")))
        if name != code:
            g.add((uri, SKOS.altLabel, Literal(code)))
        g.add((uri, FIB.recursCanonic, Literal(info["url"], datatype=XSD.anyURI)))
        n_extra += 1

    # ABox: conceptos académicos
    concept_uris = {}        # label.lower() -> uri (para skos:related)
    concept_uris_by_key = {}  # clave del diccionario -> uri (para subconcepteDe)
    for key, data in CONCEPTES.items():
        uri = FIB[f"concepte-{_slugify(key)}"]
        concept_uris[data["label"].lower()] = uri
        concept_uris_by_key[key] = uri
        # Cada concepto se tipa con su clase específica (Tramit, ProgramaMobilitat,
        # EspaiFisic...) y, además, como ConcepteAcademic para mantener
        # compatibilidad con el código existente.
        concept_class = data.get("class", "ConcepteAcademic")
        g.add((uri, RDF.type, FIB[concept_class]))
        if concept_class != "ConcepteAcademic":
            g.add((uri, RDF.type, FIB.ConcepteAcademic))
        g.add((uri, SKOS.prefLabel, Literal(data["label"], lang="ca")))
        g.add((uri, FIB.recursCanonic, Literal(data["url"], datatype=XSD.anyURI)))
        g.add((uri, FIB.pesIntencio, Literal(data["weight"], datatype=XSD.float)))
        for alt in data["alt"]:
            g.add((uri, SKOS.altLabel, Literal(alt, lang="ca")))
        for slug in data["slugs"]:
            g.add((uri, FIB.patroUrl, Literal(slug)))

    # skos:related y jerarquía subconcepteDe entre conceptos
    for key, data in CONCEPTES.items():
        uri = concept_uris_by_key[key]
        for rel_label in data.get("related", []):
            rel_uri = concept_uris.get(rel_label.lower())
            if rel_uri is not None:
                g.add((uri, SKOS.related, rel_uri))
                g.add((rel_uri, SKOS.related, uri))
        parent_key = data.get("parent")
        if parent_key:
            parent_uri = concept_uris_by_key.get(parent_key)
            if parent_uri is not None:
                g.add((uri, FIB.subconcepteDe, parent_uri))

    return g


def main():
    g = build_graph()
    g.serialize(destination=OUTPUT_TTL, format="turtle")
    n_classes = len(list(g.subjects(RDF.type, OWL.Class)))
    n_instances = len(set(g.subjects(FIB.recursCanonic, None)))
    n_assign = len(list(g.subjects(RDF.type, FIB.Assignatura)))
    print(f"Ontologia generada: {OUTPUT_TTL}")
    print(f"  Triples:      {len(g)}")
    print(f"  Classes:      {n_classes}")
    print(f"  Instancies:   {n_instances}")
    print(f"  Assignatures: {n_assign}")


if __name__ == "__main__":
    sys.exit(main())
