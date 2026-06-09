# modules/analysis/analyzer.py
"""
OSINTINATOR - Analysis & Link Intelligence Module
Performs entity resolution, relationship mapping, and heuristic scoring.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Set

from core.config import config
from core.exceptions import ModuleExecutionError
from core.models import (
    IntelligenceItem,
    WorkflowTask,
    ApiResponseEnvelope,
    Target,
)

logger = logging.getLogger(__name__)


class AnalysisHandler:
    """Handler for analysis tasks registered with Coordinator."""

    @staticmethod
    async def run(task: WorkflowTask) -> ApiResponseEnvelope:
        try:
            # Gather all intelligence collected so far
            # In real flow, this would come from coordinator, but we simulate via task
            results = await run_analysis(task.target, task.parameters.get("intelligence", []))
            return ApiResponseEnvelope(
                success=True,
                data=results,
                source="analysis"
            )
        except Exception as e:
            logger.exception("Analysis module failed")
            raise ModuleExecutionError(f"Analysis failed: {e}") from e


async def run_analysis(target: Target, intelligence_items: List[Dict] | None = None) -> Dict[str, Any]:
    """Run comprehensive analysis and link mapping."""
    intelligence_items = intelligence_items or []
    
    logger.info(f"Running analysis for target {target.id} ({target.full_name})")

    # === Entity Resolution ===
    resolved_entities = _resolve_entities(target, intelligence_items)

    # === Relationship / Link Analysis ===
    relationships = _build_relationship_graph(target, intelligence_items)

    # === Heuristic Scoring ===
    risk_score = _calculate_heuristic_score(target, intelligence_items, relationships)

    # === Key Insights Generation ===
    insights = _generate_insights(target, relationships, risk_score)

    analysis_result = {
        "content": f"Analysis completed for {target.full_name or target.id}",
        "target_id": str(target.id),
        "resolved_entities": resolved_entities,
        "relationships": relationships,
        "risk_score": risk_score,
        "insights": insights,
        "tags": ["analysis", "link-analysis", "heuristics", "india-context"],
        "timestamp": datetime.utcnow().isoformat()
    }

    logger.info(f"Analysis complete. Risk Score: {risk_score:.2f} | Relationships: {len(relationships)}")
    return analysis_result


def _resolve_entities(target: Target, intelligence: List[Dict]) -> List[Dict]:
    """Basic entity resolution (deduplication & merging)."""
    entities = []
    seen = set()

    # Add primary target
    entities.append({
        "entity_type": target.entity_type.value,
        "name": target.full_name,
        "identifiers": {
            "phones": target.phone_numbers,
            "emails": target.emails,
            "usernames": target.usernames
        }
    })
    seen.add(target.full_name.lower() if target.full_name else "")

    # Add entities from intelligence
    for item in intelligence:
        name = item.get("name") or item.get("username")
        if name and name.lower() not in seen:
            entities.append({
                "entity_type": "related_person",
                "name": name,
                "source": item.get("source"),
                "confidence": 0.7
            })
            seen.add(name.lower())

    return entities


def _build_relationship_graph(target: Target, intelligence: List[Dict]) -> List[Dict]:
    """Build simple relationship network."""
    relationships = []

    for item in intelligence:
        if item.get("username") or item.get("phone"):
            relationships.append({
                "source": target.full_name or str(target.id),
                "target": item.get("username") or item.get("phone"),
                "type": "connected_via",
                "via": item.get("source", "unknown"),
                "strength": 0.8
            })

    # Add Indian context links (UPI, Aadhaar hints)
    if target.metadata.get("indian_ids"):
        relationships.append({
            "source": target.full_name or str(target.id),
            "target": "Indian Digital Ecosystem",
            "type": "linked_via_id",
            "via": "Aadhaar/PAN/UPI",
            "strength": 0.9
        })

    return relationships


def _calculate_heuristic_score(target: Target, intelligence: List[Dict], relationships: List[Dict]) -> float:
    """Simple heuristic risk/enrichment score (0.0 - 1.0)."""
    score = 0.4  # Base score

    if target.phone_numbers:
        score += 0.2
    if target.emails:
        score += 0.15
    if target.usernames:
        score += 0.15
    if len(relationships) > 3:
        score += 0.2
    if target.metadata.get("has_indian_ids"):
        score += 0.1

    return min(0.95, score)


def _generate_insights(target: Target, relationships: List[Dict], risk_score: float) -> List[str]:
    """Generate human-readable intelligence insights."""
    insights = []

    if risk_score > 0.7:
        insights.append("High digital footprint detected - strong OSINT coverage.")
    if any("UPI" in r.get("via", "") for r in relationships):
        insights.append("Financial digital trail (UPI) identified.")
    if target.metadata.get("indian_ids", {}).get("aadhaar"):
        insights.append("Aadhaar linkage possible - high identity confidence.")

    insights.append(f"Total relationships mapped: {len(relationships)}")
    return insights


__all__ = ["AnalysisHandler", "run_analysis"]