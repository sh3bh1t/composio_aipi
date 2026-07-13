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
    verdict_correct and blocker_correct are auto-calculated and omitted
    from the worksheet to reduce manual effort.
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
        # Exclude verdict_correct and blocker_correct from the output
        # so the human doesn't have to manually grade those fields
        exclude_fields = {"verdict_correct", "blocker_correct"}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {k: v for k, v in w.model_dump().items() if k not in exclude_fields}
                    for w in worksheets
                ],
                f,
                indent=2,
                ensure_ascii=False,
            )
        logger.info(f"Audit worksheet saved to {output_path}")

    return worksheets


def _derive_verdict_and_blocker(
    auth: str, access: str, api_type: str, has_mcp: bool
) -> tuple[str, str]:
    """Deterministically derive a verdict and blocker from the effective field values.

    Returns (verdict, blocker).
    """
    auth_l = auth.strip().lower() if auth else "unknown"
    access_l = access.strip().lower() if access else "unknown"
    api_l = api_type.strip().lower() if api_type else "unknown"

    # No API at all
    if api_l in ("none", "cli only", "sdk only"):
        return "Not Feasible", "No public API available"

    # Unknown API type and no MCP
    if api_l == "unknown" and not has_mcp:
        if auth_l == "unknown" and access_l == "unknown":
            return "Unknown", "Insufficient information to assess"
        return "Moderate", "API type not documented"

    # Gated access
    if access_l == "gated":
        return "Moderate", "Requires partner/enterprise approval"

    # Self-serve with known auth and known API
    if access_l in ("self-serve", "freemium", "open source") and auth_l != "unknown" and api_l != "unknown":
        return "Easy", "None"

    # Known API but unknown auth
    if auth_l == "unknown" and api_l != "unknown":
        return "Moderate", "Authentication method not documented or unclear"

    # Fallback
    return "Moderate", "Partial information available"


def calculate_accuracy(audit_records: list[AuditRecord]) -> dict:
    """Calculate per-field accuracy from completed audit records.

    Auto-derives verdict_correct and blocker_correct by computing
    what the verdict/blocker SHOULD be from the corrected field values,
    then comparing against the pipeline's original verdict/blocker.

    Returns accuracy metrics for each field and overall.
    """
    if not audit_records:
        return {"error": "No audit records to analyze"}

    total = len(audit_records)

    # Auto-derive verdict_correct and blocker_correct
    for r in audit_records:
        # Determine effective (corrected) values for each core field
        eff_auth = r.human_auth if (not r.auth_correct and r.human_auth) else r.pipeline_auth
        eff_access = r.human_access if (not r.access_correct and r.human_access) else r.pipeline_access
        eff_api = r.human_api_type if (not r.api_type_correct and r.human_api_type) else r.pipeline_api_type
        eff_mcp = r.human_mcp if not r.mcp_correct else r.pipeline_mcp

        # Derive what the verdict and blocker SHOULD be
        derived_verdict, derived_blocker = _derive_verdict_and_blocker(
            eff_auth, eff_access, eff_api, eff_mcp
        )

        # Compare derived verdict against the pipeline's verdict
        r.verdict_correct = (
            derived_verdict.strip().lower() == r.pipeline_verdict.strip().lower()
        )
        # For blocker, just check if the pipeline flagged it correctly (both None or both present)
        pipeline_has_blocker = r.pipeline_blocker.strip().lower() not in ("none", "")
        derived_has_blocker = derived_blocker.strip().lower() not in ("none", "")
        r.blocker_correct = (pipeline_has_blocker == derived_has_blocker)

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
    
    hits = [f"{f}" for f, acc in field_accuracies[:3]]
    misses = [f"{f}" for f, acc in field_accuracies[-2:]]

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
