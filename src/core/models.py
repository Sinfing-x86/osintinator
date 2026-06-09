# core/models.py
"""
OSINTINATOR - Core Pydantic Models
Defines strict data contracts for targets, intelligence items, evidence, and reports.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class EntityType(str, Enum):
    """Primary target entity types."""
    PERSON = "person"
    SUSPECT = "suspect"
    MISSING_PERSON = "missing_person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DEVICE = "device"
    USERNAME = "username"
    PHONE = "phone"
    EMAIL = "email"


class CaseClassification(str, Enum):
    """Security classification levels (aligned with LEA standards)."""
    UNCLASSIFIED = "unclassified"
    SENSITIVE = "sensitive"
    CONFIDENTIAL = "confidential"


# ====================== Core Entities ======================
class Target(BaseModel):
    """Primary target entity (Suspect or Missing Person)."""
    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    case_id: str = Field(..., description="LEA case reference")
    entity_type: EntityType
    full_name: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    date_of_birth: Optional[datetime] = None
    last_known_location: Optional[str] = None
    phone_numbers: List[str] = Field(default_factory=list)
    emails: List[str] = Field(default_factory=list)
    usernames: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    classification: CaseClassification = CaseClassification.UNCLASSIFIED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("phone_numbers", "emails", "usernames")
    @classmethod
    def normalize_lists(cls, v: List[str]) -> List[str]:
        return [item.strip().lower() for item in v if item and item.strip()]


class IntelligenceItem(BaseModel):
    """Atomic piece of processed intelligence."""
    id: UUID = Field(default_factory=uuid4)
    target_id: UUID
    source: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    url: Optional[HttpUrl] = None
    tags: List[str] = Field(default_factory=list)
    raw_response: Optional[Dict[str, Any]] = Field(
        None, 
        description="Sanitized raw API payload (ephemeral - not persisted long-term)"
    )


class EvidenceItem(BaseModel):
    """Admissible evidence artifact."""
    id: UUID = Field(default_factory=uuid4)
    target_id: UUID
    intelligence_id: Optional[UUID] = None
    evidence_type: str = Field(..., description="photo, document, geolocation, link, etc.")
    description: str
    file_path: Optional[str] = None  # Relative path within outputs/
    hash: Optional[str] = None  # SHA-256 for integrity
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    chain_of_custody: List[Dict[str, str]] = Field(default_factory=list)


class OSINTReport(BaseModel):
    """Final admissible intelligence briefing."""
    id: UUID = Field(default_factory=uuid4)
    case_id: str
    target: Target
    intelligence_items: List[IntelligenceItem] = Field(default_factory=list)
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    summary: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    officer_id: Optional[str] = Field(None, description="Hashed or pseudonymized officer identifier")
    version: str = "1.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ====================== Utility Models ======================
class WorkflowTask(BaseModel):
    """Task definition for the Coordinator."""
    task_id: UUID = Field(default_factory=uuid4)
    target: Target
    module: str  # e.g., "username", "network", "geospatial"
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApiResponseEnvelope(BaseModel):
    """Standardized wrapper for all integration responses."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    source: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    rate_limit_remaining: Optional[int] = None

