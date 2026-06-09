# core/config.py
"""
OSINTINATOR - Configuration Management
Pydantic Settings with environment variable support and secure defaults.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    level: str = Field("INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    format: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    file_enabled: bool = False
    file_path: Path = Field(default=Path("logs/osintinator.log"))


class ApiConfig(BaseSettings):
    """Third-party API configuration (all keys loaded from environment)."""
    # Example integrations - add more as we build modules
    shodan_api_key: str | None = Field(None, description="Shodan API key")
    maltego_api_key: str | None = Field(None, description="Maltego / Transform API key")
    haveibeenpwned_api_key: str | None = Field(None, description="HIBP API key")
    numverify_api_key: str | None = Field(None, description="NumVerify phone validation")
    hunterio_api_key: str | None = Field(None, description="Hunter.io email intelligence")
    # Add more services here as we integrate them

    # General API behavior
    default_timeout: int = Field(30, gt=0, description="Default HTTP timeout in seconds")
    max_retries: int = Field(3, ge=0)
    rate_limit_per_minute: int = Field(60, gt=0)


class OutputConfig(BaseSettings):
    """Output and evidence storage settings."""
    base_dir: Path = Field(default=Path("outputs"))
    reports_dir: Path = Field(default=Path("outputs/reports"))
    evidence_dir: Path = Field(default=Path("outputs/evidence"))
    create_dirs: bool = True


class AppConfig(BaseSettings):
    """Main application configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = "development"
    
    # Core settings
    debug: bool = False
    case_id_prefix: str = "OSINT"
    officer_id: str | None = Field(None, description="Pseudonymized officer identifier")
    
    # Concurrency & performance
    max_concurrency: int = Field(20, gt=0, description="Max async workers")
    request_timeout: int = Field(30, gt=0)
    
    # Legal & compliance
    data_retention_days: int = Field(90, gt=0)
    enable_audit_logging: bool = True
    strict_privacy_mode: bool = True  # Enforces minimal PII retention
    
    # Nested configs
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


# Global singleton instance
config: AppConfig = AppConfig()


def setup_logging() -> None:
    """Configure root logger based on settings."""
    log_level = getattr(logging, config.logging.level.upper())
    
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    
    if config.logging.file_enabled:
        config.logging.file_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(config.logging.file_path))
    
    logging.basicConfig(
        level=log_level,
        format=config.logging.format,
        handlers=handlers,
        force=True,
    )
    
    # Silence noisy third-party loggers in production
    if config.environment == "production":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)


def ensure_directories() -> None:
    """Create required output directories."""
    if config.output.create_dirs:
        for directory in [
            config.output.base_dir,
            config.output.reports_dir,
            config.output.evidence_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


# Auto-initialization helper
def initialize() -> AppConfig:
    """Initialize configuration and supporting services."""
    global config
    config = AppConfig()
    
    setup_logging()
    ensure_directories()
    
    logging.info(f"OSINTINATOR initialized in {config.environment} mode")
    if config.debug:
        logging.debug(f"Full config: {config.model_dump_json(indent=2)}")
    
    return config


# Convenience access
__all__ = ["config", "AppConfig", "initialize", "setup_logging"]