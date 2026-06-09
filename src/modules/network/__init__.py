# modules/network/__init__.py
"""
OSINTINATOR - Network Intelligence Module
Handles telecom, UPI, and digital communication signals (India-focused).
"""

from .enricher import NetworkHandler, enrich_network

__all__ = ["NetworkHandler", "enrich_network"]