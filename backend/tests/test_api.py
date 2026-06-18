"""Tests de humo de la API: verifican el contrato Pydantic y las rutas."""

import os
import sys

import pytest
from fastapi.testclient import TestClient

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from api.main import app  # noqa: E402

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    payload = r.json()
    assert payload["name"] == "SemanticFIB API"
    assert "endpoints" in payload


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_modes_listed():
    r = client.get("/api/v1/modes")
    assert r.status_code == 200
    modes = r.json()
    assert set(modes.keys()) == {"bm25", "dense", "ontology", "controlled", "hybrid"}


def test_unknown_mode_returns_400():
    r = client.post("/api/v1/search", json={"query": "hola", "mode": "no-existe"})
    assert r.status_code == 400


def test_openapi_schema():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    paths = set(schema["paths"].keys())
    expected = {
        "/api/v1/health",
        "/api/v1/stats",
        "/api/v1/modes",
        "/api/v1/search",
        "/api/v1/compare",
        "/api/v1/ask",
        "/api/v1/ontology/classes",
        "/api/v1/ontology/instances",
    }
    assert expected.issubset(paths)


@pytest.mark.skipif(
    not os.path.isdir(os.path.join(_BACKEND_DIR, "..", "chroma_db")),
    reason="Requiere un indice ChromaDB poblado (ejecutar ingest.py primero)",
)
def test_stats_with_real_index():
    r = client.get("/api/v1/stats")
    assert r.status_code == 200
    payload = r.json()
    assert payload["document_count"] >= 0
    assert payload["ontology_instances"] > 0
