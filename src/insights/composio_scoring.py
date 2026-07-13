"""Composio Opportunity Scoring.

Scores each app for Composio toolkit-building opportunity.
Higher score = better candidate for a new Composio toolkit.

Score components:
  Self-Serve:     +3
  OAuth/API Key:  +2
  REST API:       +2
  Public Docs:    +2
  MCP Available:  +1
  Enterprise:     -3
  No Public API:  -5
"""

from __future__ import annotations

from src.config import settings
from src.models import FinalAppRecord, OpportunityLevel, OpportunityScore


def score_opportunity(
    record: FinalAppRecord,
    composio_has_toolkit: bool = False,
) -> OpportunityScore:
    """Score a single app for Composio integration opportunity."""
    scores = OpportunityScore(
        app_id=record.app_id,
        app_name=record.app_name,
        category=record.category,
        composio_has_toolkit=composio_has_toolkit,
    )

    # Self-serve bonus
    access = record.access_model.lower()
    if access in ("self-serve", "freemium", "open source"):
        scores.self_serve_score = settings.score_self_serve

    # Auth method bonus
    auth = record.auth_method.lower()
    if auth in ("oauth2", "api key", "bearer token"):
        scores.auth_score = settings.score_oauth_apikey

    # API type bonus
    api = record.api_type.lower()
    if api in ("rest", "mixed", "graphql"):
        scores.api_score = settings.score_rest_api

    # Public docs bonus
    if record.evidence_urls:
        scores.docs_score = settings.score_public_docs

    # MCP bonus
    if record.has_mcp:
        scores.mcp_score = settings.score_mcp_available

    # Enterprise penalty
    if access == "gated":
        scores.gated_penalty = settings.score_enterprise_gated

    # No public API penalty
    if api in ("none", "cli only"):
        scores.no_api_penalty = settings.score_no_public_api

    # Calculate total
    scores.total_score = (
        scores.self_serve_score
        + scores.auth_score
        + scores.api_score
        + scores.docs_score
        + scores.mcp_score
        + scores.gated_penalty
        + scores.no_api_penalty
    )

    # Determine level
    if scores.total_score >= 7:
        scores.level = OpportunityLevel.HIGH
    elif scores.total_score >= 3:
        scores.level = OpportunityLevel.MEDIUM
    else:
        scores.level = OpportunityLevel.LOW

    # New opportunity = high score + no existing toolkit
    scores.is_new_opportunity = (
        scores.level in (OpportunityLevel.HIGH, OpportunityLevel.MEDIUM)
        and not composio_has_toolkit
    )

    # Build rationale
    scores.rationale = _build_rationale(scores, record)

    return scores


def score_all_apps(
    records: list[FinalAppRecord],
    composio_toolkits: dict[str, bool] | None = None,
) -> list[OpportunityScore]:
    """Score all apps and return sorted by opportunity score."""
    if composio_toolkits is None:
        composio_toolkits = {}

    scores: list[OpportunityScore] = []
    for record in records:
        has_toolkit = composio_toolkits.get(record.app_name.lower(), record.composio_has_toolkit)
        score = score_opportunity(record, composio_has_toolkit=has_toolkit)
        scores.append(score)

    # Sort by total score descending
    scores.sort(key=lambda s: s.total_score, reverse=True)
    return scores


def _build_rationale(score: OpportunityScore, record: FinalAppRecord) -> list[dict]:
    """Build a human-readable rationale for the opportunity score."""
    parts: list[dict] = []

    if score.self_serve_score > 0:
        parts.append({"text": "Self-serve access", "score": score.self_serve_score, "type": "positive"})
    if score.auth_score > 0:
        parts.append({"text": f"{record.auth_method} auth", "score": score.auth_score, "type": "positive"})
    if score.api_score > 0:
        parts.append({"text": f"{record.api_type} API", "score": score.api_score, "type": "positive"})
    if score.docs_score > 0:
        parts.append({"text": "Public docs", "score": score.docs_score, "type": "positive"})
    if score.mcp_score > 0:
        parts.append({"text": "MCP available", "score": score.mcp_score, "type": "positive"})
    if score.gated_penalty < 0:
        parts.append({"text": "Enterprise gated", "score": score.gated_penalty, "type": "negative"})
    if score.no_api_penalty < 0:
        parts.append({"text": "No public API", "score": score.no_api_penalty, "type": "negative"})

    return parts
