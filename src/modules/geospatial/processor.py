# modules/geospatial/processor.py
"""
OSINTINATOR - Geospatial & Image Metadata Processor (India Context)
Extracts EXIF data, GPS coordinates, timestamps from images.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import httpx
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS, GPSTAGS

from core.config import config
from core.exceptions import ModuleExecutionError
from core.models import WorkflowTask, ApiResponseEnvelope

logger = logging.getLogger(__name__)


class GeospatialHandler:
    """Async handler for geospatial tasks."""

    @staticmethod
    async def run(task: WorkflowTask) -> ApiResponseEnvelope:
        try:
            # Look for image paths in metadata or parameters
            image_paths = task.parameters.get("image_paths", []) or \
                         task.target.metadata.get("image_paths", [])

            if not image_paths:
                return ApiResponseEnvelope(
                    success=True,
                    data={"content": "No images provided for geospatial analysis", "tags": ["skipped"]},
                    source="geospatial"
                )

            results = await process_geospatial(image_paths)
            return ApiResponseEnvelope(
                success=True,
                data=results,
                source="geospatial"
            )
        except Exception as e:
            logger.exception("Geospatial module failed")
            raise ModuleExecutionError(f"Geospatial processing failed: {e}") from e


async def process_geospatial(image_paths: list[str]) -> Dict[str, Any]:
    """Process multiple images for metadata and location data."""
    findings = []

    for img_path in image_paths:
        result = await _process_single_image(img_path)
        if result:
            findings.append(result)

    return {
        "content": f"Processed {len(image_paths)} image(s) for geospatial intelligence",
        "findings": findings,
        "tags": ["geospatial", "exif", "location"],
        "timestamp": datetime.utcnow().isoformat()
    }


async def _process_single_image(image_path: str) -> Dict[str, Any] | None:
    """Extract EXIF, GPS, and timestamp from a single image."""
    try:
        path = Path(image_path)
        if not path.exists():
            logger.warning(f"Image not found: {image_path}")
            return None

        with Image.open(path) as img:
            exif_data = {}
            gps_info = {}

            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_data[tag] = value

                    if tag == "GPSInfo":
                        for gps_tag_id, gps_value in value.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_info[gps_tag] = gps_value

            # Extract coordinates if available
            lat, lon = _convert_gps_coordinates(gps_info)

            result = {
                "file_name": path.name,
                "file_path": str(path),
                "timestamp": exif_data.get("DateTimeOriginal") or exif_data.get("DateTime"),
                "make": exif_data.get("Make"),
                "model": exif_data.get("Model"),
                "has_gps": bool(lat and lon),
                "latitude": lat,
                "longitude": lon,
                "source": "exif"
            }

            if lat and lon:
                logger.info(f"GPS data extracted from {path.name}: {lat}, {lon}")
                # Optional: Reverse geocoding (can be extended with Nominatim or Indian services)
                result["location_hint"] = await _reverse_geocode(lat, lon)

            return result

    except Exception as e:
        logger.warning(f"Failed to process image {image_path}: {e}")
        return None


def _convert_gps_coordinates(gps_info: dict) -> tuple[float | None, float | None]:
    """Convert GPS EXIF data to decimal degrees."""
    try:
        def _to_degrees(value):
            d, m, s = value
            return float(d) + float(m) / 60 + float(s) / 3600

        lat = _to_degrees(gps_info.get("GPSLatitude"))
        lon = _to_degrees(gps_info.get("GPSLongitude"))

        if gps_info.get("GPSLatitudeRef") == "S":
            lat = -lat
        if gps_info.get("GPSLongitudeRef") == "W":
            lon = -lon

        return lat, lon
    except Exception:
        return None, None


async def _reverse_geocode(lat: float, lon: float) -> str | None:
    """Basic reverse geocoding using public API (Nominatim)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
            headers = {"User-Agent": "OSINTINATOR-LEA/1.0"}
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("display_name")
    except Exception as e:
        logger.debug(f"Reverse geocoding failed: {e}")
    return None


__all__ = ["GeospatialHandler", "process_geospatial"]