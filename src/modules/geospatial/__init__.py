# modules/geospatial/__init__.py
"""
OSINTINATOR - Geospatial Intelligence Module
Image metadata extraction, EXIF parsing, and location intelligence.
"""

from .processor import GeospatialHandler, process_geospatial

__all__ = ["GeospatialHandler", "process_geospatial"]