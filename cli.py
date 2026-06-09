# cli.py
"""
OSINTINATOR - Command Line Interface
Professional CLI for Law Enforcement OSINT workflows.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import json
import logging
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from core.config import config, initialize
from core.coordinator import coordinator
from core.exceptions import handle_exception
from core.models import Target, EntityType, CaseClassification
from modules.ingestion import IngestionHandler

# Initialize Typer app with rich help
app = typer.Typer(
    name="osintinator",
    help="OSINTINATOR - Passive OSINT Engine for Law Enforcement",
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
console = Console()


@app.callback()
def callback():
    """Initialize on every command."""
    initialize()
    # Register core modules
    coordinator.register_module("ingestion", IngestionHandler.run)
    # Future modules will be registered here


@app.command("track")
def track_suspect(
    case_id: Annotated[str, typer.Option(help="LEA Case ID (e.g., FIR-2026-XXXX)")],
    name: Annotated[str, typer.Option(help="Full name of suspect")],
    phone: Annotated[list[str], typer.Option(help="Phone number(s)")] = [],
    email: Annotated[list[str], typer.Option(help="Email address(es)")] = [],
    username: Annotated[list[str], typer.Option(help="Username(s)/handle(s)")] = [],
    aadhaar: Annotated[str, typer.Option(help="Aadhaar number")] = None,
    pan: Annotated[str, typer.Option(help="PAN card number")] = None,
    location: Annotated[str, typer.Option(help="Last known location")] = None,
    classification: Annotated[str, typer.Option(help="Classification level")] = "unclassified",
) -> None:
    """Track a suspect using passive OSINT."""
    try:
        target = Target(
            case_id=case_id,
            entity_type=EntityType.SUSPECT,
            full_name=name,
            phone_numbers=phone,
            emails=email,
            usernames=username,
            last_known_location=location,
            classification=CaseClassification(classification.upper()),
            metadata={
                "indian_ids": {
                    "aadhaar": [aadhaar] if aadhaar else [],
                    "pan": [pan] if pan else []
                }
            }
        )

        rprint(f"[bold green]Starting suspect tracking for case {case_id}[/bold green]")
        
        report = asyncio.run(coordinator.run_target(target))
        
        console.print(f"\n[bold]Workflow completed successfully![/bold]")
        console.print(f"Report ID: {report.id}")
        console.print(f"Intelligence items collected: {len(report.intelligence_items)}")
        
        _print_report_summary(report)
        
    except Exception as e:
        handle_exception(e, context="CLI Track Command")
        raise typer.Exit(code=1)


@app.command("missing")
def find_missing_person(
    case_id: Annotated[str, typer.Option(help="Missing Person Case ID")],
    name: Annotated[str, typer.Option(help="Full name")],
    phone: Annotated[list[str], typer.Option(help="Known phone(s)")] = [],
    email: Annotated[list[str], typer.Option(help="Known email(s)")] = [],
    username: Annotated[list[str], typer.Option(help="Social usernames")] = [],
    last_location: Annotated[str, typer.Option(help="Last known location")] = None,
    dob: Annotated[str, typer.Option(help="Date of birth (YYYY-MM-DD)")] = None,
) -> None:
    """Initiate search for a missing person."""
    try:
        from datetime import datetime

        target = Target(
            case_id=case_id,
            entity_type=EntityType.MISSING_PERSON,
            full_name=name,
            phone_numbers=phone,
            emails=email,
            usernames=username,
            last_known_location=last_location,
            date_of_birth=datetime.fromisoformat(dob) if dob else None,
            classification=CaseClassification.SENSITIVE,
        )

        rprint(f"[bold blue]Starting missing person search for case {case_id}[/bold blue]")
        
        report = asyncio.run(coordinator.run_target(target))
        
        console.print(f"\n[bold]Missing person workflow completed.[/bold]")
        _print_report_summary(report)
        
    except Exception as e:
        handle_exception(e, context="CLI Missing Command")
        raise typer.Exit(code=1)


def _print_report_summary(report):
    """Pretty-print report summary using Rich."""
    table = Table(title="OSINTINATOR Report Summary")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Case ID", report.case_id)
    table.add_row("Target Name", report.target.full_name or "N/A")
    table.add_row("Entity Type", report.target.entity_type.value)
    table.add_row("Intelligence Items", str(len(report.intelligence_items)))
    table.add_row("Evidence Items", str(len(report.evidence_items)))
    table.add_row("Generated At", report.generated_at.strftime("%Y-%m-%d %H:%M:%S"))
    
    console.print(table)


@app.command("report")
def view_report(
    case_id: Annotated[str, typer.Argument(help="Case ID to view")],
    report_id: Annotated[str, typer.Option(help="Specific Report UUID")] = None,
) -> None:
    """View saved report JSON."""
    reports_dir = config.output.reports_dir
    pattern = f"{case_id}*.json" if not report_id else f"*{report_id}*.json"
    
    files = list(reports_dir.glob(pattern))
    if not files:
        console.print(f"[red]No report found for case {case_id}[/red]")
        raise typer.Exit(1)
    
    report_file = files[-1]
    with open(report_file) as f:
        data = json.load(f)
    
    rprint(f"[bold]Report: {report_file.name}[/bold]")
    console.print(json.dumps(data, indent=2)[:2000] + "..." if len(json.dumps(data)) > 2000 else json.dumps(data, indent=2))


@app.command("status")
def status() -> None:
    """Show system status and configuration summary."""
    console.print("[bold]OSINTINATOR Status[/bold]")
    console.print(f"Environment : {config.environment}")
    console.print(f"Debug Mode  : {config.debug}")
    console.print(f"Output Dir  : {config.output.base_dir}")
    console.print(f"Max Concurrency: {config.max_concurrency}")
    console.print(f"Strict Privacy : {config.strict_privacy_mode}")


if __name__ == "__main__":
    app()