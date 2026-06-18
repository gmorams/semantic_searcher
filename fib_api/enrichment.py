"""Enriquecimiento de la consulta con datos estructurados de la API de la FIB.

Si la API aporta algo, se inyecta como contexto adicional en el prompt del
LLM bajo el encabezado `===== DADES API FIB =====`. Si no, no se altera nada.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .client import get_client


# disparadores de agregacion (count / list por filtro)
_COUNT_KEYWORDS = re.compile(
    r"\b(quantes|quants|cuantas|cuantos|how\s+many|nombre\s+(d')?assignatur|"
    r"count\s+of|llista[a-z]*|llistat|listar?|list\s+of)\b",
    re.IGNORECASE,
)
_FIELD_KEYWORDS = {
    "codi_upc": re.compile(r"\bcodi[s]?\s+upc\b|\bcódigo[s]?\s+upc\b|\bupc\s+code\b", re.IGNORECASE),
    "credits": re.compile(r"\bcrèdits|creditos|credits|ects\b", re.IGNORECASE),
    "semestre": re.compile(r"\bsemestre|semester|quatrimestre|quadrimestre|en\s+quin\s+s\d?\b", re.IGNORECASE),
    "departament": re.compile(r"\bdepartament|departamento|department\b", re.IGNORECASE),
    "lang": re.compile(r"\bidiom[ae]|llengua|lengua|language|en\s+quina\s+llengua\b", re.IGNORECASE),
    "obligatorietats": re.compile(r"\bprerequisi|obligator|prereq|obligatorietat|requisit[s]?\b", re.IGNORECASE),
    "guia": re.compile(r"\bguia\s+docent|temari|programa\s+de\s+l|syllabus|contingut\s+de\s+la\s+assign|"
                       r"objectius?\s+de\s+(l[a']?\s*)?assignatura\b",
                       re.IGNORECASE),
}

_DEPT_KEYWORDS = re.compile(
    r"\bdepartament[s]?\s+(de\s+la\s+)?fib|quins\s+departaments|"
    r"departament[s]?\s+hi\s+ha|cuantos\s+departamentos|fib\s+departments?\b",
    re.IGNORECASE,
)
_PLAN_KEYWORDS = re.compile(
    r"\bplan[s]?\s+d['’]?estudi|plans?\s+de\s+estudio|study\s+plans?|"
    r"quins?\s+graus|quins?\s+masters?\b",
    re.IGNORECASE,
)
_ESPEC_KEYWORDS = re.compile(
    r"\bespecialitat[s]?|menció|menciones|specialit[yi]es?\b", re.IGNORECASE,
)

# filtros detectables sobre la query
_SEMESTRE_RE = re.compile(r"\b(S[1-8]|Q[12])\b")
_PLA_RE = re.compile(r"\b(GRAU|GEI|GCED|GIA|GBIO|MEI|MIRI|MDS|MAI|MUEI)\b", re.IGNORECASE)
_DEPT_RE = re.compile(r"\b(AC|CS|EIO|ESSI|ESAII|MAT|FIS|OE)\b")

# siglas de plan -> codigo que usa el campo `plans` de la API
_PLAN_MAP = {
    "GEI": "GRAU",
    "GRAU": "GRAU",
    "GCED": "GCED",
    "GIA": "GIA",
    "GBIO": "GBIO",
    "MEI": "MEI",
    "MIRI": "MIRI",
    "MDS": "MDS",
    "MAI": "MAI",
    "MUEI": "MEI",
}


def _detect_codes(entities: List[Tuple[str, str]]) -> List[str]:
    """Extrae codigos de asignatura de las entidades enlazadas."""
    out = []
    for label, url in entities or []:
        m = re.search(r"/assignatures/([A-Z0-9\-]+)/?$", url or "")
        if m:
            out.append(m.group(1).upper())
        else:
            m = re.match(r"^([A-Z0-9\-]{1,15})\b", label or "")
            if m and any(c.isdigit() or len(m.group(1)) <= 6 for c in m.group(1)):
                out.append(m.group(1).upper())
    seen = set()
    dedup = []
    for c in out:
        if c not in seen:
            seen.add(c)
            dedup.append(c)
    return dedup


def _detect_field_intents(query: str) -> List[str]:
    return [field for field, rx in _FIELD_KEYWORDS.items() if rx.search(query)]


def _detect_filters(query: str) -> Dict[str, Optional[str]]:
    sem = _SEMESTRE_RE.search(query)
    pla_raw = _PLA_RE.search(query)
    dep = _DEPT_RE.search(query)
    pla = None
    if pla_raw:
        pla = _PLAN_MAP.get(pla_raw.group(1).upper())
    return {
        "semestre": sem.group(1).upper() if sem else None,
        "pla": pla,
        "departament": dep.group(1).upper() if dep else None,
    }


def _summarise_assignatura(a: Dict[str, Any], wanted_fields: List[str]) -> str:
    sigles = a.get("sigles") or a.get("id")
    parts = [f"- {sigles} ({a.get('nom', '')})"]
    if "codi_upc" in wanted_fields or wanted_fields == []:
        parts.append(f"  codi_upc: {a.get('codi_upc', '?')}")
    if "credits" in wanted_fields or wanted_fields == []:
        parts.append(f"  credits: {a.get('credits', '?')}")
    if "semestre" in wanted_fields or wanted_fields == []:
        parts.append(f"  semestre: {a.get('semestre', '?')}")
    if "departament" in wanted_fields or wanted_fields == []:
        parts.append(f"  departament: {a.get('departament', '?')}")
    if "lang" in wanted_fields:
        parts.append(f"  llengues: {a.get('lang', {})}")
    if "obligatorietats" in wanted_fields:
        obl = a.get("obligatorietats") or []
        for o in obl:
            parts.append(
                f"  obligatorietat: {o.get('codi_oblig')} / pla {o.get('pla')}"
                f" / esp {o.get('nom_especialitat') or '-'}"
            )
    parts.append(f"  plans: {', '.join(a.get('plans') or [])}")
    parts.append(f"  vigent: {a.get('vigent')}")
    return "\n".join(parts)


def enrich_query(
    query: str,
    entities: Optional[List[Tuple[str, str]]] = None,
    *,
    max_items: int = 25,
) -> Optional[str]:
    """Construye un bloque de texto con datos de la API relevantes. None si nada."""
    if not query or not query.strip():
        return None

    client = get_client()
    blocks: List[str] = []

    # 1) resolucion por codigo de asignatura
    codes = _detect_codes(entities or [])
    wanted_fields = _detect_field_intents(query)
    for code in codes[:5]:
        a = client.assignatura(code)
        if not a:
            continue
        blocks.append(
            f"Assignatura {code} (font: API FIB /assignatures/{code}/):\n"
            + _summarise_assignatura(a, wanted_fields)
        )
        if "guia" in wanted_fields:
            guia = client.assignatura_guia(code)
            if guia and isinstance(guia, dict):
                snippet_keys = ("objectius", "temari", "metodologia", "avaluacio",
                                "objectives", "syllabus", "methodology", "assessment")
                fragments = []
                for k, v in guia.items():
                    if isinstance(v, str) and v.strip() and any(sk in k.lower() for sk in snippet_keys):
                        fragments.append(f"  {k}: {v.strip()[:400]}")
                if fragments:
                    blocks.append("Guia docent (fragments):\n" + "\n".join(fragments[:6]))

    # 2) count / list con filtros
    if _COUNT_KEYWORDS.search(query) or wanted_fields:
        filters = _detect_filters(query)
        if any(filters.values()):
            items = client.assignatures_by(
                pla=filters["pla"],
                semestre=filters["semestre"],
                departament=filters["departament"],
            )
            header = (
                f"Filtre aplicat -> pla={filters['pla']}, semestre={filters['semestre']},"
                f" departament={filters['departament']}"
            )
            sample = "\n".join(
                f"- {a.get('sigles')} ({a.get('nom')}) [s={a.get('semestre')}, dept={a.get('departament')}]"
                for a in items[:max_items]
            )
            blocks.append(
                f"Cataleg API FIB (filtre):\n{header}\nTotal coincidencies: {len(items)}\n"
                + (sample or "(cap resultat)")
            )

    # 3) recursos auxiliares
    if _DEPT_KEYWORDS.search(query):
        deps = client.departaments()
        if deps:
            sample = "\n".join(
                f"- {d.get('sigles')}: {d.get('nom')} (cap: {d.get('cap')})" for d in deps[:25]
            )
            blocks.append(f"Departaments de la FIB (API): total {len(deps)}\n{sample}")
    if _PLAN_KEYWORDS.search(query):
        plans = client.plans_estudi()
        if plans:
            sample = "\n".join(
                f"- {p.get('sigles', p.get('codi', '?'))}: {p.get('nom')}" for p in plans[:25]
            )
            blocks.append(f"Plans d'estudi (API): total {len(plans)}\n{sample}")
    if _ESPEC_KEYWORDS.search(query):
        esps = client.especialitats()
        if esps:
            sample = "\n".join(
                f"- {e.get('sigles', '?')}: {e.get('nom')} ({e.get('codi_pla', '?')})"
                for e in esps[:25]
            )
            blocks.append(f"Especialitats (API): total {len(esps)}\n{sample}")

    if not blocks:
        return None
    return "===== DADES API FIB (estructurades) =====\n" + "\n\n".join(blocks) + "\n===== FI =====\n"
