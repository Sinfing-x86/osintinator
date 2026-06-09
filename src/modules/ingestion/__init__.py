# modules/ingestion/__init__.py
"""
OSINTINATOR - Ingestion Module
Target normalization, validation, and initial entity extraction.
"""

from .normalizer import normalize_target, IngestionHandler

__all__ = ["normalize_target", "IngestionHandler"]