"""Vinculacio d'entitats (entity linking) guiada per l'ontologia.

Detecta a la consulta codis d'assignatura (XC, PRO1, EDA...), sigles de
titulacions (GEI, GCED, MIRI...) i les resol a la seva pagina web canonica,
definida com a instancia de l'ontologia (fib:recursCanonic).

Regles de matching (per evitar falsos positius amb paraules normals):
  - Codis amb digits (PRO1, M1, AC2):    insensible a majuscules.
  - Codis de 1-2 lletres (A, G, XC, BD): nomes si apareixen en majuscules.
  - Codis de 3+ lletres (EDA, PROP):     insensible a majuscules, excepte
    els que coincideixen amb paraules reals (CAP, PES, PAR, MAI, SI...),
    que requereixen majuscules.
"""

import re

from ontology.fib_ontology import get_ontology

# Codis/sigles que tambe son paraules en catala/castella: nomes en majuscules
AMBIGUOUS_CODES = {"CAP", "PES", "PAR", "MAI", "BIO", "SOA", "IES", "EDO", "ROB"}


def _token_matches(code, query):
    """Comprova si el codi apareix com a token independent a la consulta."""
    has_digit = any(ch.isdigit() for ch in code)
    if has_digit or (len(code) >= 3 and code.upper() not in AMBIGUOUS_CODES):
        pattern = re.compile(r"\b" + re.escape(code) + r"\b", re.IGNORECASE)
    else:
        pattern = re.compile(r"\b" + re.escape(code) + r"\b")  # exacte (majuscules)
    return bool(pattern.search(query))


def extract_entities(query):
    """Retorna [(etiqueta, url)] de les entitats detectades a la consulta."""
    ontology = get_ontology()
    entities = []
    seen = set()

    for code, course in ontology.course_index().items():
        if _token_matches(code, query) and course["url"] not in seen:
            seen.add(course["url"])
            label = course["label"] if course["label"] != code else code
            entities.append((f"{code} ({label})" if label != code else code, course["url"]))

    for acronym, degree in ontology.acronym_index().items():
        if _token_matches(acronym, query) and degree["url"] not in seen:
            seen.add(degree["url"])
            entities.append((f"{acronym} ({degree['label']})", degree["url"]))

    return entities
