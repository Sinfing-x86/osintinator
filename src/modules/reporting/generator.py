# modules/reporting/generator.py
"""
OSINTINATOR - Professional Report Generation
Uses Jinja2 to create admissible intelligence briefing documents.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.config import config
from core.models import OSINTReport
from core.exceptions import ReportGenerationError

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Handles HTML + future PDF report generation."""

    def __init__(self):
        self.template_dir = Path("templates")
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    async def generate(self, report: OSINTReport) -> Path:
        """Generate HTML briefing and return file path."""
        try:
            template = self.env.get_template("report_theme.html")
            
            # Enrich metadata for template
            report_dict = report.model_dump()
            report_dict["metadata"]["insights"] = report.metadata.get("insights", [
                f"Total Intelligence Items: {len(report.intelligence_items)}",
                "Passive OSINT only - Legally compliant workflow"
            ])

            html_content = template.render(report=report_dict)

            output_path = config.output.reports_dir / f"{report.case_id}_{report.id}.html"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info(f"Intelligence briefing generated: {output_path}")
            return output_path

        except Exception as e:
            logger.exception("Report generation failed")
            raise ReportGenerationError(f"Failed to generate report: {e}") from e


# Global instance
report_generator = ReportGenerator()


async def generate_briefing(report: OSINTReport) -> Path:
    """Convenience function."""
    return await report_generator.generate(report)


__all__ = ["ReportGenerator", "generate_briefing", "report_generator"]