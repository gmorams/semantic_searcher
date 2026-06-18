"""Entrada de la API HTTP de SemanticFIB."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import chat, ontology, search, system

API_PREFIX = "/api/v1"

app = FastAPI(
    title="SemanticFIB API",
    description=(
        "API HTTP del buscador semántico de la FIB. Expone los cinco modos de "
        "recuperación (BM25, vectorial, expansión ontológica, controlada e "
        "híbrida RRF), el pipeline RAG conversacional y el grafo de la ontología."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


_allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(system.router, prefix=API_PREFIX, tags=["system"])
app.include_router(search.router, prefix=API_PREFIX, tags=["search"])
app.include_router(chat.router, prefix=API_PREFIX, tags=["chat"])
app.include_router(ontology.router, prefix=API_PREFIX, tags=["ontology"])


@app.get("/")
def root():
    return {
        "name": "SemanticFIB API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [f"{API_PREFIX}/health", f"{API_PREFIX}/stats", f"{API_PREFIX}/ask"],
    }
