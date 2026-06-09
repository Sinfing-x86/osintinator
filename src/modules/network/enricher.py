# modules/network/enricher.py
"""
OSINTINATOR - Network & Telecom Enrichment (India Context)
Passive lookups for phone numbers, UPI handles, and carrier information.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

import httpx

from core.config import config
from core.exceptions import ModuleExecutionError
from core.models import WorkflowTask, ApiResponseEnvelope

logger = logging.getLogger(__name__)


class NetworkHandler:
    """Async handler for network-related tasks."""

    @staticmethod
    async def run(task: WorkflowTask) -> ApiResponseEnvelope:
        try:
            phones = task.target.phone_numbers
            upi_handles = task.target.metadata.get("upi_handles", [])

            if not phones and not upi_handles:
                return ApiResponseEnvelope(
                    success=True,
                    data={"content": "No network identifiers provided", "tags": ["skipped"]},
                    source="network"
                )

            results = await enrich_network(phones, upi_handles)
            return ApiResponseEnvelope(
                success=True,
                data=results,
                source="network"
            )
        except Exception as e:
            logger.exception("Network module failed")
            raise ModuleExecutionError(f"Network enrichment failed: {e}") from e


async def enrich_network(phones: list[str], upi_handles: list[str]) -> Dict[str, Any]:
    """Enrich phone numbers and UPI handles."""
    findings = []

    async with httpx.AsyncClient(timeout=config.api.default_timeout) as client:
        # Phone number enrichment
        for phone in phones:
            result = await _enrich_phone(client, phone)
            if result:
                findings.append(result)

        # UPI enrichment
        for upi in upi_handles:
            result = await _enrich_upi(client, upi)
            if result:
                findings.append(result)

    return {
        "content": f"Enriched {len(phones)} phone(s) and {len(upi_handles)} UPI handle(s)",
        "findings": findings,
        "tags": ["network", "telecom", "upi", "india-context"],
        "timestamp": datetime.utcnow().isoformat()
    }


async def _enrich_phone(client: httpx.AsyncClient, phone: str) -> Dict[str, Any] | None:
    """Enrich a single Indian phone number."""
    # Example using public/free tier APIs (NumVerify, etc.)
    try:
        # NumVerify example (add your key in .env)
        if config.api.numverify_api_key:
            url = f"http://apilayer.net/api/validate?access_key={config.api.numverify_api_key}&number={phone}"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "type": "phone",
                    "identifier": phone,
                    "carrier": data.get("carrier"),
                    "location": data.get("location"),
                    "line_type": data.get("line_type"),
                    "valid": data.get("valid"),
                    "source": "numverify"
                }
    except Exception as e:
        logger.debug(f"NumVerify failed for {phone}: {e}")

    # Fallback carrier prefix lookup (India-specific)
    prefix = phone[-10:-7] if len(phone) >= 10 else ""
    common_carriers = {
        "701": "Airtel", "702": "Airtel", "703": "Airtel",
        "704": "BSNL", "708": "BSNL",
        "987": "Airtel", "988": "Airtel", "989": "Airtel",
        "999": "Vodafone", "98": "Jio"
    }

    carrier = common_carriers.get(prefix[:3]) or "Unknown"

    return {
        "type": "phone",
        "identifier": phone,
        "carrier": carrier,
        "country": "IN",
        "source": "prefix_lookup",
        "confidence": 0.6
    }


async def _enrich_upi(client: httpx.AsyncClient, upi: str) -> Dict[str, Any] | None:
    """Basic UPI handle intelligence."""
    return {
        "type": "upi",
        "identifier": upi,
        "platform": "UPI",
        "content": f"UPI handle detected: {upi}",
        "tags": ["financial", "digital_payment"],
        "source": "metadata"
    }


__all__ = ["NetworkHandler", "enrich_network"]