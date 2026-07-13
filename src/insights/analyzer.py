"""Insights Analyzer — generates aggregate statistics and headline findings.

Takes the final dataset and produces InsightsSummary with:
- Distributions (auth, access, API, MCP, categories)
- Rankings (blockers, opportunities)
- Headline metrics for the executive summary
"""

from __future__ import annotations

from collections import Counter

from src.models import FinalAppRecord, InsightsSummary, OpportunityScore


def generate_insights(
    records: list[FinalAppRecord],
    opportunity_scores: list[OpportunityScore] | None = None,
    audit_accuracy: dict | None = None,
) -> InsightsSummary:
    """Generate comprehensive insights from the final dataset."""
    insights = InsightsSummary(total_apps=len(records))

    # ── Distributions ──
    insights.auth_distribution = dict(Counter(r.auth_method for r in records))
    insights.access_distribution = dict(Counter(r.access_model for r in records))
    insights.api_type_distribution = dict(Counter(r.api_type for r in records))
    insights.category_distribution = dict(Counter(r.category for r in records))
    insights.verdict_distribution = dict(Counter(r.build_verdict for r in records))

    # MCP distribution
    mcp_yes = sum(1 for r in records if r.has_mcp)
    insights.mcp_distribution = {
        "Has MCP": mcp_yes,
        "No MCP": len(records) - mcp_yes,
    }

    # ── Headline Metrics ──
    total = len(records) or 1

    # Self-serve vs gated
    self_serve = sum(
        1 for r in records
        if r.access_model.lower() in ("self-serve", "freemium", "open source")
    )
    gated = sum(1 for r in records if r.access_model.lower() == "gated")
    insights.pct_self_serve = round(self_serve / total * 100, 1)
    insights.pct_gated = round(gated / total * 100, 1)

    # Dominant auth
    auth_counts = Counter(r.auth_method for r in records)
    if auth_counts:
        insights.dominant_auth = auth_counts.most_common(1)[0][0]

    # MCP percentage
    insights.pct_mcp_available = round(mcp_yes / total * 100, 1)

    # Average confidence
    confidences = [r.confidence_score for r in records if r.confidence_score > 0]
    insights.avg_confidence = round(
        sum(confidences) / len(confidences), 3
    ) if confidences else 0.0

    # ── Blockers ──
    blocker_counts = Counter(
        r.main_blocker for r in records
        if r.main_blocker and r.main_blocker.lower() != "none"
    )
    insights.top_blockers = [
        {"blocker": blocker, "count": count}
        for blocker, count in blocker_counts.most_common(10)
    ]

    # ── Opportunity Rankings ──
    if opportunity_scores:
        # Most promising category
        cat_scores: dict[str, list[int]] = {}
        for score in opportunity_scores:
            cat_scores.setdefault(score.category, []).append(score.total_score)

        if cat_scores:
            avg_cat_scores = {
                cat: sum(scores) / len(scores)
                for cat, scores in cat_scores.items()
            }
            insights.most_promising_category = max(
                avg_cat_scores, key=avg_cat_scores.get  # type: ignore
            )

        # Top opportunities
        top_opps = [
            s for s in opportunity_scores
            if s.is_new_opportunity
        ][:15]
        insights.top_opportunities = [
            {
                "app": s.app_name,
                "category": s.category,
                "score": s.total_score,
                "level": s.level.value,
                "rationale": s.rationale,
            }
            for s in top_opps
        ]

    # ── Audit Accuracy ──
    if audit_accuracy:
        per_field = audit_accuracy.get("per_field_accuracy", {})
        insights.accuracy_after_verification = per_field.get("overall", 0.0)
        insights.total_corrections = audit_accuracy.get("total_corrections", 0)

        # Extract lessons from corrections
        corrections = audit_accuracy.get("corrections", [])
        if corrections:
            field_errors = Counter(c["field"] for c in corrections)
            insights.lessons_learned = [
                f"Most errors in '{field}' field ({count} corrections)"
                for field, count in field_errors.most_common(3)
            ]

    return insights
