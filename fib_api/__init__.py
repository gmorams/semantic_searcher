"""Integracion con la API publica de fib.upc.edu (api.fib.upc.edu/v2/)."""

from .client import FIBApiClient, get_client
from .enrichment import enrich_query

__all__ = ["FIBApiClient", "get_client", "enrich_query"]
