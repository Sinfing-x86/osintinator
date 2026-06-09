# modules/analysis/__init__.py
"""
OSINTINATOR - Analysis Module
Link analysis, entity resolution, and heuristic intelligence fusion.
"""

from .analyzer import AnalysisHandler, run_analysis

__all__ = ["AnalysisHandler", "run_analysis"]