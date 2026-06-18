"""Cliente HTTP minimo para la API publica de la FIB (v2).

Singleton con cache en memoria. Si la API no responde, los metodos devuelven
None o lista vacia: el enriquecimiento es aditivo, nunca bloquea al RAG.
"""

from __future__ import annotations

import os
import time
import threading
from typing import Any, Dict, List, Optional

import requests

DEFAULT_BASE = "https://api.fib.upc.edu/v2"
DEFAULT_CLIENT_ID = "BHaoxq1Fr0xe3o9BBpcz7kPhunbVn7W0CR4URr4c"
DEFAULT_TIMEOUT = 10
DEFAULT_TTL_SECONDS = 60 * 60  # cache de 1 hora
USER_AGENT = "SemanticFIB-TFG/1.0 (Academic Research - UPC FIB)"


class FIBApiClient:
    """Cliente HTTP con cache para la API publica de la FIB."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        base_url: str = DEFAULT_BASE,
        lang: str = "ca",
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.client_id = client_id or os.getenv("FIB_API_CLIENT_ID", DEFAULT_CLIENT_ID)
        self.base_url = base_url.rstrip("/")
        self.lang = lang
        self.ttl = ttl_seconds
        self.timeout = timeout
        self._cache: Dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # HTTP base
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "client_id": self.client_id,
            "Accept": "application/json",
            "Accept-Language": self.lang,
            "User-Agent": USER_AGENT,
        }

    def _get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        cache_key = url + "?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))

        with self._lock:
            cached = self._cache.get(cache_key)
            if cached and (time.time() - cached[0] < self.ttl):
                return cached[1]

        try:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=self.timeout)
            if resp.status_code != 200:
                return None
            data = resp.json()
        except Exception:
            return None

        with self._lock:
            self._cache[cache_key] = (time.time(), data)
        return data

    def _get_all_pages(self, path: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Recorre todas las paginas (recursos paginados con `next`)."""
        out: List[Dict[str, Any]] = []
        next_url: Optional[str] = path
        first = True
        while next_url:
            data = self._get_json(next_url, params if first else None)
            first = False
            if not data:
                break
            if isinstance(data, dict) and "results" in data:
                out.extend(data.get("results") or [])
                next_url = data.get("next")
            elif isinstance(data, list):
                out.extend(data)
                break
            else:
                break
        return out

    # ------------------------------------------------------------------
    # Recursos publicos (se cachean en el primer hit)
    # ------------------------------------------------------------------

    def all_assignatures(self) -> List[Dict[str, Any]]:
        return self._get_all_pages("/assignatures/", {"lang": self.lang})

    def assignatura(self, sigles: str) -> Optional[Dict[str, Any]]:
        """Detalle de una asignatura por sus siglas."""
        if not sigles:
            return None
        return self._get_json(f"/assignatures/{sigles}/", {"lang": self.lang})

    def assignatura_guia(self, sigles: str) -> Optional[Dict[str, Any]]:
        """Guia docente completa (objetivos, temario, metodologia...)."""
        if not sigles:
            return None
        return self._get_json(f"/assignatures/{sigles}/guia/", {"lang": self.lang})

    def departaments(self) -> List[Dict[str, Any]]:
        return self._get_all_pages("/departaments/", {"lang": self.lang})

    def plans_estudi(self) -> List[Dict[str, Any]]:
        return self._get_all_pages("/plans_estudi/", {"lang": self.lang})

    def especialitats(self) -> List[Dict[str, Any]]:
        return self._get_all_pages("/especialitats/", {"lang": self.lang})

    def quadrimestres(self) -> List[Dict[str, Any]]:
        return self._get_all_pages("/quadrimestres/", {"lang": self.lang})

    def aules(self) -> List[Dict[str, Any]]:
        return self._get_all_pages("/aules/", {"lang": self.lang})

    def professors(self) -> List[Dict[str, Any]]:
        return self._get_all_pages("/professors/", {"lang": self.lang})

    # ------------------------------------------------------------------
    # Filtros sobre el catalogo de asignaturas
    # ------------------------------------------------------------------

    def assignatures_by(
        self,
        pla: Optional[str] = None,
        semestre: Optional[str] = None,
        departament: Optional[str] = None,
        especialitat: Optional[str] = None,
        vigent: bool = True,
    ) -> List[Dict[str, Any]]:
        items = self.all_assignatures()
        if not items:
            return []
        out = []
        for a in items:
            if vigent and a.get("vigent") not in ("S", "Si", "Sí", True):
                continue
            if pla and pla not in (a.get("plans") or []):
                continue
            if semestre and (a.get("semestre") or "").upper() != semestre.upper():
                continue
            if departament and (a.get("departament") or "").upper() != departament.upper():
                continue
            if especialitat:
                esp = especialitat.upper()
                obligs = a.get("obligatorietats") or []
                if not any(esp == (o.get("codi_especialitat") or "").upper() for o in obligs):
                    continue
            out.append(a)
        return out


_INSTANCE: Optional[FIBApiClient] = None
_INSTANCE_LOCK = threading.Lock()


def get_client(**kwargs) -> FIBApiClient:
    global _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = FIBApiClient(**kwargs)
    return _INSTANCE
