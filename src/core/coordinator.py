# core/coordinator.py
"""
OSINTINATOR - Workflow Coordinator
Central async orchestration engine for the full intelligence lifecycle.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict

from uuid import UUID

from .config import config, initialize
from .exceptions import OSINTinatorError, ModuleExecutionError
from .models import (
    Target,
    IntelligenceItem,
    EvidenceItem,
    OSINTReport,
    WorkflowTask,
    ApiResponseEnvelope,
)

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """Registry for modular task handlers."""
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
    
    def register(self, module_name: str, handler: Callable):
        """Register an async module handler."""
        self.handlers[module_name] = handler
        logger.debug(f"Registered module: {module_name}")
    
    def get_handler(self, module_name: str) -> Callable | None:
        return self.handlers.get(module_name)


class Coordinator:
    """
    Main orchestration engine.
    Manages the end-to-end lifecycle: Target → Ingestion → Enrichment → Analysis → Reporting.
    """
    
    def __init__(self):
        self.registry = ModuleRegistry()
        self.tasks: list[WorkflowTask] = []
        self.intelligence: list[IntelligenceItem] = []
        self.evidence: list[EvidenceItem] = []
        self._semaphore: asyncio.Semaphore | None = None
    
    async def initialize(self) -> None:
        """Initialize coordinator and global config."""
        initialize()
        self._semaphore = asyncio.Semaphore(config.max_concurrency)
        logger.info("OSINTINATOR Coordinator initialized")
    
    def register_module(self, module_name: str, handler: Callable[[WorkflowTask], Coroutine]):
        """Register async module handlers (e.g. username, network, etc.)."""
        self.registry.register(module_name, handler)
    
    async def _execute_task(self, task: WorkflowTask) -> None:
        """Execute a single task with concurrency control and error handling."""
        async with self._semaphore:
            handler = self.registry.get_handler(task.module)
            if not handler:
                logger.warning(f"No handler registered for module: {task.module}")
                task.status = "failed"
                return
            
            try:
                logger.info(f"Executing {task.module}.{task.action} for target {task.target.id}")
                result: ApiResponseEnvelope | dict = await handler(task)
                
                if isinstance(result, dict):
                    result = ApiResponseEnvelope(success=True, data=result, source=task.module)
                
                if result.success and result.data:
                    # Convert successful results into IntelligenceItem(s)
                    self._process_task_result(task, result)
                    task.status = "completed"
                else:
                    task.status = "failed"
                    logger.error(f"Task failed: {result.error}")
                    
            except Exception as e:
                task.status = "failed"
                logger.exception(f"Task {task.task_id} failed")
                raise ModuleExecutionError(f"Module {task.module} failed: {e}") from e
    
    def _process_task_result(self, task: WorkflowTask, envelope: ApiResponseEnvelope) -> None:
        """Convert API/module results into intelligence and evidence artifacts."""
        data = envelope.data
        
        if isinstance(data, list):
            items = data
        else:
            items = [data] if data else []
        
        for item in items:
            if isinstance(item, dict):
                intel = IntelligenceItem(
                    target_id=task.target.id,
                    source=envelope.source,
                    content=str(item.get("content") or item),
                    url=item.get("url"),
                    tags=item.get("tags", []),
                    raw_response=item if config.debug else None,
                )
                self.intelligence.append(intel)
    
    async def run_target(self, target: Target) -> OSINTReport:
        """
        Execute full intelligence lifecycle for a single target.
        """
        logger.info(f"Starting OSINT workflow for case {target.case_id} | Target: {target.full_name or target.id}")
        
        self.tasks.clear()
        self.intelligence.clear()
        self.evidence.clear()
        
        # === Phase 1: Ingestion & Validation ===
        ingestion_task = WorkflowTask(
            target=target,
            module="ingestion",
            action="normalize",
            parameters={"raw_target": target}
        )
        self.tasks.append(ingestion_task)
        await self._execute_task(ingestion_task)
        
        # === Phase 2: Parallel Enrichment Modules ===
        enrichment_modules = ["username", "network", "geospatial"]  # Extend as modules are built
        
        enrichment_tasks = [
            WorkflowTask(
                target=target,
                module=mod,
                action="enrich",
                parameters={}
            )
            for mod in enrichment_modules
            if mod in self.registry.handlers
        ]
        
        if enrichment_tasks:
            await asyncio.gather(
                *[self._execute_task(t) for t in enrichment_tasks],
                return_exceptions=True
            )
            self.tasks.extend(enrichment_tasks)
        
        # === Phase 3: Analysis & Report Generation ===
        report = self._generate_report(target)
        
        logger.info(f"Completed workflow for case {target.case_id}. "
                   f"Intelligence items: {len(self.intelligence)} | Evidence: {len(self.evidence)}")
        
        return report
    
    def _generate_report(self, target: Target) -> OSINTReport:
        """Generate final OSINTReport with all collected artifacts."""
        report = OSINTReport(
            case_id=target.case_id,
            target=target,
            intelligence_items=self.intelligence.copy(),
            evidence_items=self.evidence.copy(),
            summary=self._generate_summary(),
            officer_id=config.officer_id,
            metadata={
                "total_tasks": len(self.tasks),
                "completed_tasks": sum(1 for t in self.tasks if t.status == "completed"),
                "runtime": datetime.utcnow().isoformat()
            }
        )
        
        # Persist report
        self._save_report(report)
        return report
    
    def _generate_summary(self) -> str:
        """Basic executive summary."""
        return (
            f"OSINTINATOR Report - {len(self.intelligence)} intelligence items collected. "
            f"Target enriched across {len({t.module for t in self.tasks})} modules."
        )
    
    def _save_report(self, report: OSINTReport) -> Path:
        """Save report as JSON (extendable to PDF via Jinja2 later)."""
        output_path = config.output.reports_dir / f"{report.case_id}_{report.id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))
        
        logger.info(f"Report saved: {output_path}")
        return output_path


# Global coordinator instance
coordinator: Coordinator = Coordinator()


__all__ = ["Coordinator", "coordinator", "ModuleRegistry"]