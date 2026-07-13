"""Confidence Scoring — composite confidence for each app's classification.

Combines evidence availability, deterministic matches, model agreement,
and evidence quality into a single 0-1 score.
"""

from __future__ import annotations

from src.config import settings
from src.models import (
    ConfidenceLevel,
    ConfidenceScore,
    EvidenceBundle,
    VerificationResult,
)


def compute_confidence(
    bundle: EvidenceBundle,
    verification: VerificationResult,
) -> ConfidenceScore:
    """Compute composite confidence score for an app.

    Weights:
    - Evidence availability: 0.20 (docs found?)
    - Deterministic matches: 0.20 (keyword patterns hit?)
    - Model agreement: 0.30 (primary + verifier agree?)
    - Evidence quality: 0.30 (snippet quality + specificity)
    """
    # 1. Evidence availability (0.0 - 0.2)
    evidence_score = 0.2 if bundle.has_documentation else 0.0

    # 2. Deterministic match score (0.0 - 0.2)
    det_signals = 0
    if bundle.detected_auth_methods:
        det_signals += 1
    if bundle.detected_api_types:
        det_signals += 1
    if bundle.detected_access_signals:
        det_signals += 1
    if bundle.detected_mcp_signals:
        det_signals += 0.5
    deterministic_score = min(0.2, (det_signals / 3.5) * 0.2)

    # 3. Model agreement score (0.0 - 0.3)
    if verification.field_verifications:
        agree_count = sum(1 for fv in verification.field_verifications if fv.agrees)
        total = len(verification.field_verifications)
        agreement_ratio = agree_count / total if total > 0 else 0.5
    else:
        agreement_ratio = 0.5
    agreement_score = agreement_ratio * 0.3

    # 4. Evidence quality score (0.0 - 0.3)
    quality_map = {"high": 0.3, "medium": 0.2, "low": 0.1, "none": 0.0}
    quality_score = quality_map.get(bundle.evidence_quality, 0.0)

    # Total
    total = evidence_score + deterministic_score + agreement_score + quality_score
    total = min(1.0, max(0.0, total))

    # Determine level
    if total >= settings.confidence_high:
        level = ConfidenceLevel.HIGH
    elif total >= settings.confidence_medium:
        level = ConfidenceLevel.MEDIUM
    elif total >= settings.confidence_low:
        level = ConfidenceLevel.LOW
    else:
        level = ConfidenceLevel.NEEDS_REVIEW

    return ConfidenceScore(
        app_id=bundle.app_id,
        evidence_score=round(evidence_score, 3),
        deterministic_score=round(deterministic_score, 3),
        agreement_score=round(agreement_score, 3),
        quality_score=round(quality_score, 3),
        total_score=round(total, 3),
        level=level,
    )
