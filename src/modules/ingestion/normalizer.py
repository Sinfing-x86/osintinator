# modules/ingestion/normalizer.py
"""
OSINTINATOR - Target Ingestion & Normalization (India-focused)
Handles parsing, cleaning, and standardization of Indian targets:
Phones (+91), Aadhaar, PAN, Names, Emails, Usernames, UPI.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict

import phonenumbers
from email_validator import EmailNotValidError, validate_email
from pydantic import ValidationError

from core.config import config
from core.exceptions import IngestionError
from core.models import (
    Target,
    EntityType,
    WorkflowTask,
    ApiResponseEnvelope,
)

logger = logging.getLogger(__name__)


# Indian-specific patterns
INDIAN_PHONE_REGEX = re.compile(r'^(?:\+91|91|0)?[6-9]\d{9}$')
PAN_REGEX = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
AADHAAR_REGEX = re.compile(r'^\d{4}\s?\d{4}\s?\d{4}$')  # or 12 continuous digits


class IngestionHandler:
    """Handler class for ingestion tasks (registered with Coordinator)."""
    
    @staticmethod
    async def run(task: WorkflowTask) -> ApiResponseEnvelope:
        """Main entry point for ingestion tasks."""
        try:
            result = await normalize_target(task.target, task.parameters)
            return ApiResponseEnvelope(
                success=True,
                data=result,
                source="ingestion",
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            logger.exception("Ingestion failed")
            return ApiResponseEnvelope(
                success=False,
                error=str(e),
                source="ingestion"
            )


async def normalize_target(raw_target: Target, parameters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Normalize and enrich a Target object with Indian context awareness.
    """
    parameters = parameters or {}
    logger.info(f"Normalizing Indian-context target for case {raw_target.case_id}")

    target = raw_target.model_copy(deep=True)

    # === Name Normalization (Indian names often multi-part) ===
    if target.full_name:
        # Handle common Indian name formats (e.g., First Middle Last, with titles)
        name_parts = re.split(r'\s+', target.full_name.strip())
        target.full_name = " ".join(part.title() for part in name_parts)
        target.aliases = [a.strip().title() for a in target.aliases if a]

    # === Indian Phone Number Normalization ===
    normalized_phones = []
    for phone in target.phone_numbers:
        # Clean and try Indian-specific logic
        cleaned = re.sub(r'[\s\-\(\)]+', '', phone)
        if INDIAN_PHONE_REGEX.match(cleaned) or cleaned.startswith('+91'):
            try:
                parsed = phonenumbers.parse(phone, "IN")
                if phonenumbers.is_valid_number(parsed):
                    formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                    normalized_phones.append(formatted)
                    logger.debug(f"Validated Indian phone: {phone} → {formatted}")
                else:
                    logger.warning(f"Invalid Indian phone: {phone}")
            except Exception as e:
                logger.warning(f"phonenumbers lib failed for {phone}: {e}")
                # Fallback accept if matches regex
                if INDIAN_PHONE_REGEX.match(cleaned):
                    normalized_phones.append(f"+91{cleaned[-10:]}")
        else:
            logger.warning(f"Non-Indian or invalid phone skipped: {phone}")

    target.phone_numbers = list(dict.fromkeys(normalized_phones))  # dedup

    # === Email Normalization ===
    normalized_emails = []
    for email in target.emails:
        try:
            valid = validate_email(email, check_deliverability=False)
            normalized_emails.append(valid.normalized.lower())
        except EmailNotValidError:
            logger.warning(f"Invalid email skipped: {email}")

    target.emails = normalized_emails

    # === Username / Social Handle Cleaning ===
    target.usernames = [
        re.sub(r"[^\w.-]", "", u.strip().lower()) for u in target.usernames if u and u.strip()
    ]

    # === Indian ID Documents (Aadhaar, PAN) ===
    aadhaar_list = []
    pan_list = []
    metadata_ids = target.metadata.setdefault("indian_ids", {})

    for item in target.metadata.get("raw_ids", []):
        cleaned = re.sub(r'\s+', '', str(item).upper())
        if len(cleaned) == 12 and cleaned.isdigit() and AADHAAR_REGEX.match(re.sub(r'\s+', ' ', str(item))):
            aadhaar_list.append(cleaned)
        elif PAN_REGEX.match(cleaned):
            pan_list.append(cleaned)

    if aadhaar_list:
        metadata_ids["aadhaar"] = aadhaar_list
    if pan_list:
        metadata_ids["pan"] = pan_list

    # === UPI Handle Normalization ===
    upi_handles = target.metadata.get("upi_handles", [])
    target.metadata["upi_handles"] = [
        h.lower() + "@upi" if "@" not in h else h.lower()
        for h in upi_handles if h
    ]

    # === Entity Type Inference (India context) ===
    if not target.entity_type or target.entity_type == EntityType.PERSON:
        if any(target.phone_numbers) or metadata_ids.get("aadhaar") or metadata_ids.get("pan"):
            target.entity_type = EntityType.SUSPECT if "suspect" in target.case_id.lower() else EntityType.PERSON

    # === Rich Metadata for Indian Context ===
    target.metadata.update({
        "normalized_at": datetime.utcnow().isoformat(),
        "ingestion_version": "1.1-india",
        "country_context": "IN",
        "source_modules_ready": ["username", "network", "geospatial"],
        "has_indian_ids": bool(metadata_ids.get("aadhaar") or metadata_ids.get("pan")),
    })

    target.updated_at = datetime.utcnow()

    logger.info(
        f"Indian-context normalization complete. "
        f"Phones: {len(target.phone_numbers)}, Emails: {len(target.emails)}, "
        f"Aadhaar: {len(metadata_ids.get('aadhaar', []))}, PAN: {len(metadata_ids.get('pan', []))}"
    )

    return {
        "normalized_target": target.model_dump(mode="json"),
        "content": f"Target {target.id} normalized with Indian context",
        "tags": ["normalized", "ingested", "india-context"]
    }


__all__ = ["normalize_target", "IngestionHandler"]