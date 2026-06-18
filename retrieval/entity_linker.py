"""
Entity linking guiado por la ontología: detecta códigos de asignatura y siglas
de titulación en la consulta y los resuelve a su página canónica.
"""

import re

from ontology.fib_ontology import get_ontology

# Códigos/siglas que también son palabras comunes: solo cuentan si van en mayúsculas
AMBIGUOUS_CODES = {"CAP", "PES", "PAR", "MAI", "BIO", "SOA", "IES", "EDO", "ROB"}


def _token_matches(code, query, *, strict_boundary=False):
    """¿El código aparece como token independiente en la consulta?

    Con strict_boundary=True no contamos como match si el código está pegado a
    un guion u otro alfanumérico — así MDS dentro de BSG-MDS no se confunde
    con la sigla del máster.
    """
    has_digit = any(ch.isdigit() for ch in code)
    if strict_boundary:
        # ningún alfanumérico ni guion delante o detrás
        left = r"(?<![-\w])"
        right = r"(?![-\w])"
    else:
        left = right = r"\b"

    if has_digit or (len(code) >= 3 and code.upper() not in AMBIGUOUS_CODES):
        pattern = re.compile(left + re.escape(code) + right, re.IGNORECASE)
    else:
        pattern = re.compile(left + re.escape(code) + right)  # match exacto (mayúsculas)
    return bool(pattern.search(query))


def extract_entities(query):
    """[(etiqueta, url)] de las entidades detectadas."""
    ontology = get_ontology()
    entities = []
    seen = set()

    for code, course in ontology.course_index().items():
        if _token_matches(code, query) and course["url"] not in seen:
            seen.add(course["url"])
            label = course["label"] if course["label"] != code else code
            entities.append((f"{code} ({label})" if label != code else code, course["url"]))

    # Las siglas de titulación van con matching estricto: son cortas y a menudo
    # aparecen embebidas en códigos de asignatura (MDS dentro de BSG-MDS).
    for acronym, degree in ontology.acronym_index().items():
        if _token_matches(acronym, query, strict_boundary=True) and degree["url"] not in seen:
            seen.add(degree["url"])
            entities.append((f"{acronym} ({degree['label']})", degree["url"]))

    return entities
