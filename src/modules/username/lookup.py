# modules/username/lookup.py
"""
OSINTINATOR - Username Enrichment Module (India-focused)
Performs passive lookups on major platforms.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

import httpx

from core.config import config
from core.exceptions import ModuleExecutionError
from core.models import WorkflowTask, ApiResponseEnvelope

logger = logging.getLogger(__name__)

# Platform configurations (expandable)
PLATFORMS = {
    "twitter": {"url": "https://api.twitter.com/2/users/by/username/{username}", "needs_key": True},
    "instagram": {"url": "https://www.instagram.com/{username}/", "needs_key": False},  # Public scrape simulation
    "facebook": {"url": "https://www.facebook.com/{username}", "needs_key": False},
    "github": {"url": "https://api.github.com/users/{username}", "needs_key": False},
    "linkedin": {"url": "https://www.linkedin.com/in/{username}", "needs_key": False},
    # Indian platforms
    "sharechat": {"url": "https://sharechat.com/user/{username}", "needs_key": False},
    "moj": {"url": "https://mojapp.in/user/{username}", "needs_key": False},
    "instagram_india": {"url": "https://www.instagram.com/{username}/", "needs_key": False},
}


class UsernameHandler:
    """Async handler registered with Coordinator."""

    @staticmethod
    async def run(task: WorkflowTask) -> ApiResponseEnvelope:
        try:
            usernames = task.target.usernames
            if not usernames:
                return ApiResponseEnvelope(
                    success=True,
                    data={"content": "No usernames provided", "tags": ["skipped"]},
                    source="username"
                )

            results = await enrich_username(usernames)
            return ApiResponseEnvelope(
                success=True,
                data=results,
                source="username"
            )
        except Exception as e:
            logger.exception("Username module failed")
            raise ModuleExecutionError(f"Username enrichment failed: {e}") from e


async def enrich_username(usernames: List[str]) -> Dict[str, Any]:
    """Enrich multiple usernames in parallel."""
    async with httpx.AsyncClient(timeout=config.api.default_timeout) as client:
        tasks = [check_single_username(client, username) for username in usernames]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_results = []
    for res in results:
        if isinstance(res, dict):
            valid_results.append(res)

    return {
        "content": f"Checked {len(usernames)} username(s)",
        "usernames_checked": usernames,
        "findings": valid_results,
        "tags": ["username", "social", "india-context"]
    }


async def check_single_username(client: httpx.AsyncClient, username: str) -> Dict[str, Any] | None:
    """Check username availability/existence on multiple platforms."""
    findings = {"username": username, "platforms": {}}

    for platform, info in PLATFORMS.items():
        try:
            url = info["url"].format(username=username)
            headers = {"User-Agent": "OSINTINATOR-LEA/1.0"}

            resp = await client.get(url, headers=headers, follow_redirects=True)

            if resp.status_code == 200:
                findings["platforms"][platform] = {
                    "exists": True,
                    "url": url,
                    "status": "active"
                }
                logger.info(f"✓ {username} found on {platform}")
            elif resp.status_code == 404:
                findings["platforms"][platform] = {"exists": False}
            else:
                findings["platforms"][platform] = {"status": "unknown", "code": resp.status_code}

        except Exception as e:
            logger.debug(f"Error checking {platform} for {username}: {e}")

    return findings if any(p.get("exists") for p in findings["platforms"].values()) else None


__all__ = ["UsernameHandler", "enrich_username"]