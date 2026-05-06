"""
Paquet de sincronització de catàleg (OpenAPI Movies API v1).

Vegeu ``sync_catalog.sync_catalog_from_apis`` i el docstring del projecte sobre alineació OpenAPI.
"""
from .constants import CATALOG_REF_SOURCE
from .sync_catalog import sync_catalog_from_apis

__all__ = ["CATALOG_REF_SOURCE", "sync_catalog_from_apis"]
