"""Human Audit Framework.

Selects 30 apps (3 per category) for manual verification.
Generates audit worksheets, processes human corrections,
and calculates per-field accuracy metrics.
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from src.config import settings
from src.models import AuditRecord, FinalAppRecord

logger = logging.getLogger(__name__)


def select_audit_sample(
    apps: list[dict],
    per_category: int = 3,
    seed: int = 42,
) -> list[dict]:
    """Select apps for human audit — N random from each category.

    Args:
        apps: List of app dicts with 'id', 'name', 'category_id', 'category_name'
        per_category: Number of apps to sample per category
        seed: Random seed for reproducibility

    Returns:
        List of selected app dicts
    """
    rng = random.Random(seed)

    # Group by category
    by_category: dict[int, list[dict]] = {}
    for app in apps:
        cat_id = app.get("category_id", 0)
        by_category.setdefault(cat_id, []).append(app)

    selected: list[dict] = []
    for cat_id in sorted(by_category.keys()):
        cat_apps = by_category[cat_id]
        sample_size = min(per_category, len(cat_apps))
        sampled = rng.sample(cat_apps, sample_size)
        selected.extend(sampled)

    logger.info(
        f"Selected {len(selected)} apps for audit "
        f"({per_category} per category, {len(by_category)} categories)"
    )
    return selected


def generate_audit_worksheet(
    audit_apps: list[dict],
    final_records: list[FinalAppRecord],
    output_path: Path | None = None,
) -> list[AuditRecord]:
    """Generate audit worksheet with pipeline values pre-filled.

    The human auditor fills in 'human_*' fields and marks correctness.
    """
    records_by_id = {r.app_id: r for r in final_records}
    worksheets: list[AuditRecord] = []

    for app in audit_apps:
        record = records_by_id.get(app["id"])
        if not record:
            logger.warning(f"No final record for audit app {app['name']}")
            continue

        worksheet = AuditRecord(
            app_id=app["id"],
            app_name=app["name"],
            category=record.category,
            pipeline_auth=record.auth_method,
            pipeline_access=record.access_model,
            pipeline_api_type=record.api_type,
            pipeline_mcp=record.has_mcp,
            pipeline_verdict=record.build_verdict,
            pipeline_blocker=record.main_blocker,
            pipeline_urls=record.evidence_urls,
            # Human fields left empty for manual filling
        )
        worksheets.append(worksheet)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [w.model_dump() for w in worksheets],
                f,
                indent=2,
                ensure_ascii=False,
            )
        logger.info(f"Audit worksheet saved to {output_path}")

    return worksheets


def calculate_accuracy(audit_records: list[AuditRecord]) -> dict:
    """Calculate per-field accuracy from completed audit records.

    Returns accuracy metrics for each field and overall.
    """
    if not audit_records:
        return {"error": "No audit records to analyze"}

    total = len(audit_records)
    fields = ["auth", "access", "api_type", "mcp", "verdict", "blocker"]

    accuracy: dict[str, float] = {}
    for field in fields:
        correct_count = sum(
            1 for r in audit_records if getattr(r, f"{field}_correct", False)
        )
        accuracy[field] = round(correct_count / total, 3) if total > 0 else 0.0

    # Overall accuracy (average of all fields)
    accuracy["overall"] = round(
        sum(accuracy.values()) / len(accuracy), 3
    )

    # Corrections summary
    corrections: list[dict] = []
    for record in audit_records:
        for field in fields:
            if not getattr(record, f"{field}_correct", True):
                pipeline_val = getattr(record, f"pipeline_{field}", "")
                human_val = getattr(record, f"human_{field}", "")
                if human_val:  # Only count if human provided a value
                    corrections.append({
                        "app": record.app_name,
                        "field": field,
                        "pipeline_value": str(pipeline_val),
                        "human_value": str(human_val),
                    })

    # Calculate dynamic Hits (top 3) and Misses (bottom 2) based on real field accuracy
    # Only use basic fields (exclude overall)
    field_accuracies = [(f, accuracy[f]) for f in fields]
    # Sort by accuracy descending
    field_accuracies.sort(key=lambda x: x[1], reverse=True)
    
    hits = [f"{f} ({acc*100:.1f}%)" for f, acc in field_accuracies[:3]]
    misses = [f"{f} ({acc*100:.1f}%)" for f, acc in field_accuracies[-2:]]

    return {
        "total_audited": total,
        "per_field_accuracy": accuracy,
        "total_corrections": len(corrections),
        "corrections": corrections,
        "dynamic_hits": hits,
        "dynamic_misses": misses,
    }


def apply_audit_corrections(
    final_records: list[FinalAppRecord],
    audit_records: list[AuditRecord],
) -> list[FinalAppRecord]:
    """Apply human audit corrections back to the final dataset.

    Only overrides fields where the human provided a correction.
    """
    audit_by_id = {r.app_id: r for r in audit_records}
    corrected_count = 0

    for record in final_records:
        audit = audit_by_id.get(record.app_id)
        if not audit:
            continue

        record.was_audited = True
        corrections: list[str] = []

        # Apply corrections where human disagrees and provided a value
        if not audit.auth_correct and audit.human_auth:
            corrections.append(f"auth: {record.auth_method} → {audit.human_auth}")
            record.auth_method = audit.human_auth

        if not audit.access_correct and audit.human_access:
            corrections.append(f"access: {record.access_model} → {audit.human_access}")
            record.access_model = audit.human_access

        if not audit.api_type_correct and audit.human_api_type:
            corrections.append(f"api_type: {record.api_type} → {audit.human_api_type}")
            record.api_type = audit.human_api_type

        if not audit.mcp_correct:
            corrections.append(f"mcp: {record.has_mcp} → {audit.human_mcp}")
            record.has_mcp = audit.human_mcp

        if not audit.verdict_correct and audit.human_verdict:
            corrections.append(f"verdict: {record.build_verdict} → {audit.human_verdict}")
            record.build_verdict = audit.human_verdict

        if not audit.blocker_correct and audit.human_blocker:
            corrections.append(f"blocker: {record.main_blocker} → {audit.human_blocker}")
            record.main_blocker = audit.human_blocker

        record.audit_corrections = corrections
        if corrections:
            corrected_count += 1

    logger.info(f"Applied corrections to {corrected_count}/{len(audit_records)} audited apps")
    return final_records
