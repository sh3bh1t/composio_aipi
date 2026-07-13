"""Entry point for the Composio Research Pipeline.

Usage:
  # Run full pipeline
  .\venv\Scripts\python.exe run.py

  # Run with resume (skip completed stages)
  .\venv\Scripts\python.exe run.py --resume

  # Run specific stage
  .\venv\Scripts\python.exe run.py --stage discovery
  .\venv\Scripts\python.exe run.py --stage classify
  .\venv\Scripts\python.exe run.py --stage verify
  .\venv\Scripts\python.exe run.py --stage report

  # Generate audit worksheet
  .\venv\Scripts\python.exe run.py --audit
"""

import argparse
import sys

from rich.console import Console

console = Console()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Composio AI Product Ops Research Pipeline"
    )
    parser.add_argument(
        "--stage",
        choices=["all", "discovery", "extract", "classify", "verify", "report", "insights"],
        default="all",
        help="Run a specific pipeline stage (default: all)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint (skip completed stages)",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Generate human audit worksheet",
    )

    args = parser.parse_args()

    try:
        if args.audit:
            _run_audit()
        elif args.stage == "all":
            from src.pipeline import run_full_pipeline
            run_full_pipeline(resume=args.resume)
        elif args.stage == "discovery":
            from src.pipeline import load_app_seeds, run_discovery, setup_logging
            setup_logging()
            apps, _ = load_app_seeds()
            run_discovery(apps, resume=args.resume)
        elif args.stage == "extract":
            from src.pipeline import (
                load_app_seeds, run_discovery, run_extraction, setup_logging
            )
            setup_logging()
            apps, _ = load_app_seeds()
            discoveries = run_discovery(apps, resume=True)
            run_extraction(discoveries, apps, resume=args.resume)
        elif args.stage == "classify":
            from src.pipeline import (
                load_app_seeds, run_extraction, run_discovery,
                run_classification, setup_logging
            )
            setup_logging()
            apps, _ = load_app_seeds()
            discoveries = run_discovery(apps, resume=True)
            bundles = run_extraction(discoveries, apps, resume=True)
            run_classification(bundles, resume=args.resume)
        elif args.stage == "verify":
            from src.pipeline import (
                load_app_seeds, run_discovery, run_extraction,
                run_classification, run_verification, setup_logging
            )
            setup_logging()
            apps, _ = load_app_seeds()
            discoveries = run_discovery(apps, resume=True)
            bundles = run_extraction(discoveries, apps, resume=True)
            classifications = run_classification(bundles, resume=True)
            run_verification(bundles, classifications, resume=args.resume)
        elif args.stage == "report":
            _run_report_only()
        elif args.stage == "insights":
            _run_report_only()

    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted. Use --resume to continue.[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Pipeline error: {e}[/]")
        raise


def _run_audit() -> None:
    """Generate audit worksheet from existing results."""
    import json
    from src.config import settings
    from src.pipeline import load_app_seeds, setup_logging
    from src.verification.audit import select_audit_sample, generate_audit_worksheet
    from src.models import FinalAppRecord

    setup_logging()
    apps, _ = load_app_seeds()

    # Load final dataset
    final_path = settings.get_data_path(settings.final_dataset_json)
    if not final_path.exists():
        console.print("[red]No final dataset found. Run full pipeline first.[/]")
        return

    with open(final_path, "r", encoding="utf-8") as f:
        records = [FinalAppRecord(**r) for r in json.load(f)]

    # Select audit sample
    audit_apps = select_audit_sample(apps, per_category=settings.audit_per_category)

    # Generate worksheet
    output_path = settings.get_data_path(settings.audit_worksheet_file)
    generate_audit_worksheet(audit_apps, records, output_path)

    console.print(f"[green]Audit worksheet saved: {output_path}[/]")
    console.print(f"[yellow]Edit the worksheet to fill in human_* fields and *_correct flags[/]")


def _run_report_only() -> None:
    """Regenerate HTML report from existing data."""
    import json
    from src.config import settings
    from src.pipeline import setup_logging
    from src.models import FinalAppRecord, OpportunityScore
    from src.insights.analyzer import generate_insights

    setup_logging()

    # Load final dataset
    final_path = settings.get_data_path(settings.final_dataset_json)
    if not final_path.exists():
        console.print("[red]No final dataset found. Run full pipeline first.[/]")
        return

    with open(final_path, "r", encoding="utf-8") as f:
        records = [FinalAppRecord(**r) for r in json.load(f)]

    # Check for manual audit worksheet
    audit_path = settings.get_data_path(settings.audit_worksheet_file)
    audit_accuracy = None
    if audit_path.exists():
        console.print("[yellow]Found manual audit worksheet. Applying corrections...[/]")
        from src.models import AuditRecord
        from src.verification.audit import calculate_accuracy, apply_audit_corrections
        
        with open(audit_path, "r", encoding="utf-8") as f:
            audit_records = [AuditRecord(**r) for r in json.load(f)]
            
        audit_accuracy = calculate_accuracy(audit_records)
        records = apply_audit_corrections(records, audit_records)
        
        # Save the applied corrections back to the final dataset
        with open(final_path, "w", encoding="utf-8") as f:
            json.dump([r.model_dump() for r in records], f, indent=2, default=str)
        console.print(f"  [green]Overall Human Audit Accuracy: {audit_accuracy['per_field_accuracy']['overall'] * 100:.1f}%[/]")

    # Re-score opportunities
    from src.insights.composio_scoring import score_all_apps
    opp_scores = score_all_apps(records)

    # Generate insights
    insights = generate_insights(records, opp_scores, audit_accuracy)

    # Generate HTML
    from src.report.generator import generate_html_report
    html_path = generate_html_report(records, insights, opp_scores)
    console.print(f"[bold green]Report generated: {html_path}[/]")


if __name__ == "__main__":
    main()
