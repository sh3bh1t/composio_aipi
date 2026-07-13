"""Main Pipeline Orchestrator.

Coordinates all stages of the research pipeline with:
- Checkpoint/resume support (JSON after each stage)
- Progress tracking via rich console
- Error handling with graceful degradation
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.logging import RichHandler

from src.config import settings
from src.models import (
    ConfidenceScore,
    DiscoveryResult,
    EvidenceBundle,
    FinalAppRecord,
    ResearchResult,
    VerificationResult,
)

console = Console()
logger = logging.getLogger("pipeline")


def setup_logging() -> None:
    """Configure rich logging for the pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


# ─── Data Loading ────────────────────────────────────────────────────────────


def load_app_seeds() -> tuple[list[dict], dict[int, str]]:
    """Load app seeds and return (flat_apps_list, category_map)."""
    seeds_path = settings.get_data_path(settings.app_seeds_file)
    with open(seeds_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    apps: list[dict] = []
    cat_map: dict[int, str] = {}

    for category in data.get("categories", []):
        cat_id = category["category_id"]
        cat_name = category["category_name"]
        cat_map[cat_id] = cat_name

        for app in category.get("apps", []):
            app["category_id"] = cat_id
            app["category_name"] = cat_name
            apps.append(app)

    console.print(f"[bold green]Loaded {len(apps)} apps across {len(cat_map)} categories[/]")
    return apps, cat_map


def save_checkpoint(data: list, filename: str) -> Path:
    """Save intermediate results to JSON checkpoint."""
    path = settings.get_data_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    serializable = []
    for item in data:
        if hasattr(item, "model_dump"):
            serializable.append(item.model_dump())
        elif isinstance(item, dict):
            serializable.append(item)
        else:
            serializable.append(str(item))

    with open(path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False, default=str)

    console.print(f"[dim]Checkpoint saved: {path}[/]")
    return path


def load_checkpoint(filename: str) -> list[dict] | None:
    """Load checkpoint if it exists."""
    path = settings.get_data_path(filename)
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    console.print(f"[yellow]Loaded checkpoint: {path} ({len(data)} items)[/]")
    return data


# ─── Pipeline Stages ─────────────────────────────────────────────────────────


def run_discovery(apps: list[dict], resume: bool = False) -> list[DiscoveryResult]:
    """Stage 1: Documentation Discovery."""
    console.rule("[bold blue]Stage 1: Documentation Discovery")

    if resume:
        cached = load_checkpoint(settings.discovery_results_file)
        if cached:
            return [DiscoveryResult(**item) for item in cached]

    # Lazy load to avoid circular dependency during module initialization
    from src.agents.doc_discovery import discover_all_apps

    results = asyncio.run(discover_all_apps(apps))

    # Report summary
    success = sum(1 for r in results if r.discovery_success)
    console.print(
        f"[green]Discovery complete: {success}/{len(results)} apps found docs[/]"
    )

    save_checkpoint(results, settings.discovery_results_file)
    return results


def run_extraction(
    discoveries: list[DiscoveryResult],
    apps: list[dict],
    resume: bool = False,
) -> list[EvidenceBundle]:
    """Stage 2: Evidence Extraction."""
    console.rule("[bold blue]Stage 2: Evidence Extraction")

    if resume:
        cached = load_checkpoint(settings.evidence_bundles_file)
        if cached:
            return [EvidenceBundle(**item) for item in cached]

    # Lazy load to avoid circular dependency during module initialization
    from src.extraction.evidence_builder import extract_evidence

    # Build category lookup
    cat_lookup = {app["id"]: app.get("category_name", "") for app in apps}

    bundles: list[EvidenceBundle] = []
    for discovery in discoveries:
        bundle = extract_evidence(
            discovery,
            category_name=cat_lookup.get(discovery.app_id, ""),
        )
        bundles.append(bundle)

    # Report
    with_evidence = sum(1 for b in bundles if b.evidence_quality != "none")
    high_quality = sum(1 for b in bundles if b.evidence_quality == "high")
    console.print(
        f"[green]Extraction complete: {with_evidence} with evidence, "
        f"{high_quality} high quality[/]"
    )

    save_checkpoint(bundles, settings.evidence_bundles_file)
    return bundles


def run_classification(
    bundles: list[EvidenceBundle],
    resume: bool = False,
) -> list[ResearchResult]:
    """Stage 3: LLM Classification."""
    console.rule("[bold blue]Stage 3: LLM Classification (Primary)")

    if resume:
        cached = load_checkpoint(settings.classification_results_file)
        if cached:
            return [ResearchResult(**item) for item in cached]

    # Lazy load to avoid circular dependency during module initialization
    from src.agents.classifier import classify_batch

    console.print(
        f"[yellow]Classifying {len(bundles)} apps with {settings.primary_model}...[/]"
    )

    results = asyncio.run(classify_batch(bundles))

    save_checkpoint(results, settings.classification_results_file)
    return results


def run_verification(
    bundles: list[EvidenceBundle],
    classifications: list[ResearchResult],
    resume: bool = False,
) -> list[VerificationResult]:
    """Stage 4: Verification."""
    console.rule("[bold blue]Stage 4: Verification (Secondary)")

    if resume:
        cached = load_checkpoint(settings.verification_results_file)
        if cached:
            return [VerificationResult(**item) for item in cached]

    # Lazy load to avoid circular dependency during module initialization
    from src.agents.verifier import verify_batch

    console.print(
        f"[yellow]Verifying {len(bundles)} apps with {settings.verification_model}...[/]"
    )

    results = asyncio.run(verify_batch(bundles, classifications))

    save_checkpoint(results, settings.verification_results_file)
    return results


def run_confidence_scoring(
    bundles: list[EvidenceBundle],
    verifications: list[VerificationResult],
) -> list[ConfidenceScore]:
    """Stage 5: Confidence Scoring."""
    console.rule("[bold blue]Stage 5: Confidence Scoring")

    # Lazy load to avoid circular dependency during module initialization
    from src.verification.confidence import compute_confidence

    bundle_by_id = {b.app_id: b for b in bundles}
    verify_by_id = {v.app_id: v for v in verifications}

    scores: list[ConfidenceScore] = []
    for app_id in bundle_by_id:
        bundle = bundle_by_id[app_id]
        verification = verify_by_id.get(
            app_id,
            VerificationResult(app_id=app_id, app_name=bundle.app_name),
        )
        score = compute_confidence(bundle, verification)
        scores.append(score)

    # Report
    high = sum(1 for s in scores if s.level.value == "High")
    medium = sum(1 for s in scores if s.level.value == "Medium")
    low = sum(1 for s in scores if s.level.value == "Low")
    review = sum(1 for s in scores if s.level.value == "Needs Review")
    console.print(
        f"[green]Confidence: High={high}, Medium={medium}, Low={low}, "
        f"Needs Review={review}[/]"
    )

    return scores


def build_final_dataset(
    apps: list[dict],
    classifications: list[ResearchResult],
    verifications: list[VerificationResult],
    confidence_scores: list[ConfidenceScore],
    opportunity_scores: list | None = None,
) -> list[FinalAppRecord]:
    """Merge all results into the final dataset."""
    console.rule("[bold blue]Building Final Dataset")

    # Lazy load to avoid circular dependency during module initialization
    from src.agents.verifier import resolve_disagreements

    class_by_id = {c.app_id: c for c in classifications}
    verify_by_id = {v.app_id: v for v in verifications}
    conf_by_id = {c.app_id: c for c in confidence_scores}
    opp_by_id = {}
    if opportunity_scores:
        opp_by_id = {o.app_id: o for o in opportunity_scores}

    records: list[FinalAppRecord] = []

    for app in apps:
        app_id = app["id"]
        classification = class_by_id.get(app_id)
        verification = verify_by_id.get(app_id)
        confidence = conf_by_id.get(app_id)

        if not classification:
            # No classification — create empty record
            records.append(FinalAppRecord(
                app_id=app_id,
                app_name=app["name"],
                category=app.get("category_name", ""),
            ))
            continue

        # Resolve disagreements
        if verification:
            resolved = resolve_disagreements(classification, verification)
        else:
            resolved = classification

        opp = opp_by_id.get(app_id)

        record = FinalAppRecord(
            app_id=app_id,
            app_name=app["name"],
            category=app.get("category_name", resolved.category),
            one_line_description=app.get("hint", ""),
            auth_method=resolved.auth_method.value,
            access_model=resolved.access_model.value,
            api_type=resolved.api_type.value,
            has_mcp=resolved.has_mcp,
            mcp_details=resolved.mcp_details,
            build_verdict=resolved.build_verdict.value,
            main_blocker=resolved.main_blocker,
            evidence_urls=resolved.evidence_urls,
            confidence_score=confidence.total_score if confidence else 0.0,
            confidence_level=confidence.level.value if confidence else "Needs Review",
            composio_has_toolkit=opp.composio_has_toolkit if opp else False,
            opportunity_score=opp.total_score if opp else 0,
            opportunity_level=opp.level.value if opp else "Low",
        )
        records.append(record)

    console.print(f"[green]Final dataset: {len(records)} apps[/]")
    save_checkpoint(records, settings.final_dataset_json)

    # Also save CSV
    _save_csv(records)

    return records


def _save_csv(records: list[FinalAppRecord]) -> None:
    """Save final dataset as CSV for easy viewing."""
    import pandas as pd

    rows = [r.model_dump() for r in records]
    df = pd.DataFrame(rows)

    # Flatten evidence_urls list to string
    df["evidence_urls"] = df["evidence_urls"].apply(
        lambda x: "; ".join(x) if isinstance(x, list) else str(x)
    )
    df["audit_corrections"] = df["audit_corrections"].apply(
        lambda x: "; ".join(x) if isinstance(x, list) else str(x)
    )

    csv_path = settings.get_data_path(settings.final_dataset_csv)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    console.print(f"[dim]CSV saved: {csv_path}[/]")


# ─── Full Pipeline ───────────────────────────────────────────────────────────


def run_full_pipeline(resume: bool = False) -> list[FinalAppRecord]:
    """Run the complete research pipeline end-to-end."""
    setup_logging()

    console.print("[bold magenta]═══ Composio AI Product Ops Research Pipeline ═══[/]")
    console.print()

    # Load seeds
    apps, cat_map = load_app_seeds()

    # Stage 1: Discovery
    discoveries = run_discovery(apps, resume=resume)

    # Stage 2: Evidence extraction
    bundles = run_extraction(discoveries, apps, resume=resume)

    # Stage 3: Classification
    classifications = run_classification(bundles, resume=resume)

    # Stage 4: Verification
    verifications = run_verification(bundles, classifications, resume=resume)

    # Stage 5: Confidence scoring
    confidence_scores = run_confidence_scoring(bundles, verifications)

    # Stage 6: Composio opportunity scoring
    console.rule("[bold blue]Stage 6: Opportunity Scoring")
    # Lazy load to avoid circular dependency during module initialization
    from src.insights.composio_checker import check_composio_toolkits
    from src.insights.composio_scoring import score_all_apps
    
    app_names = [app["name"] for app in apps]
    toolkits = asyncio.run(check_composio_toolkits(app_names))
    
    opportunity_scores = score_all_apps(
        _build_temp_records(apps, classifications),
        composio_toolkits=toolkits,
    )

    # Stage 7: Build final dataset
    final_records = build_final_dataset(
        apps, classifications, verifications, confidence_scores, opportunity_scores
    )

    # Stage 8: Generate insights
    console.rule("[bold blue]Stage 7: Generating Insights")
    # Lazy load to avoid circular dependency during module initialization
    from src.insights.analyzer import generate_insights
    insights = generate_insights(final_records, opportunity_scores)

    insights_path = settings.get_data_path("insights_summary.json")
    with open(insights_path, "w", encoding="utf-8") as f:
        json.dump(insights.model_dump(), f, indent=2, default=str)

    # Stage 9: Generate HTML report
    console.rule("[bold blue]Stage 8: Generating HTML Report")
    # Lazy load to avoid circular dependency during module initialization
    from src.report.generator import generate_html_report
    html_path = generate_html_report(final_records, insights, opportunity_scores)
    console.print(f"[bold green]Report generated: {html_path}[/]")

    # Summary
    console.print()
    console.rule("[bold green]Pipeline Complete")
    console.print(f"[bold]Total apps: {len(final_records)}[/]")
    console.print(f"[bold]Self-serve: {insights.pct_self_serve}%[/]")
    console.print(f"[bold]Dominant auth: {insights.dominant_auth}[/]")
    console.print(f"[bold]MCP available: {insights.pct_mcp_available}%[/]")
    console.print(f"[bold]Avg confidence: {insights.avg_confidence:.2f}[/]")

    return final_records


def _build_temp_records(
    apps: list[dict], classifications: list[ResearchResult]
) -> list[FinalAppRecord]:
    """Build temporary FinalAppRecord list for opportunity scoring."""
    class_by_id = {c.app_id: c for c in classifications}
    records = []
    for app in apps:
        c = class_by_id.get(app["id"])
        if c:
            records.append(FinalAppRecord(
                app_id=app["id"],
                app_name=app["name"],
                category=app.get("category_name", c.category),
                auth_method=c.auth_method.value,
                access_model=c.access_model.value,
                api_type=c.api_type.value,
                has_mcp=c.has_mcp,
                build_verdict=c.build_verdict.value,
                main_blocker=c.main_blocker,
                evidence_urls=c.evidence_urls,
            ))
        else:
            records.append(FinalAppRecord(
                app_id=app["id"],
                app_name=app["name"],
                category=app.get("category_name", ""),
            ))
    return records

if __name__ == "__main__":
    run_full_pipeline(resume=True)
