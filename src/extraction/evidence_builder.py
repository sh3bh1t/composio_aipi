"""Evidence Extraction Engine.

Takes raw text from doc discovery and produces compact EvidenceBundle objects.
This is the critical bridge between crawling and LLM classification.

Strategy:
1. Run all keyword patterns against raw text
2. Extract relevant snippets (paragraphs containing keywords)
3. Score evidence quality
4. Package into compact bundle (< 800 tokens for LLM)
"""

from __future__ import annotations

import logging
import re

from src.extraction.keyword_patterns import (
    AUTH_PATTERNS,
    API_TYPE_PATTERNS,
    ACCESS_PATTERNS,
    BLOCKER_PATTERNS,
    MCP_PATTERNS,
    get_unique_labels,
)
from src.models import DiscoveryResult, EvidenceBundle, KeywordMatch

logger = logging.getLogger(__name__)


def extract_evidence(
    discovery: DiscoveryResult,
    category_name: str = "",
    max_snippets: int = 5,
    max_snippet_length: int = 500,
) -> EvidenceBundle:
    """Build an evidence bundle from discovery results.

    Runs deterministic keyword extraction, then selects the most
    relevant text snippets to include for LLM classification.
    """
    text = discovery.raw_text

    bundle = EvidenceBundle(
        app_id=discovery.app_id,
        app_name=discovery.app_name,
        hint=discovery.hint,
        category_name=category_name,
        has_documentation=discovery.discovery_success,
        docs_url=_best_url(discovery),
    )

    if not text:
        bundle.evidence_quality = "none"
        return bundle

    # ── Run all pattern groups ──
    auth_matches = AUTH_PATTERNS.find_matches_with_context(text)
    api_matches = API_TYPE_PATTERNS.find_matches_with_context(text)
    access_matches = ACCESS_PATTERNS.find_matches_with_context(text)
    mcp_matches = MCP_PATTERNS.find_matches_with_context(text)
    blocker_matches = BLOCKER_PATTERNS.find_matches_with_context(text)

    # ── Store keyword matches ──
    all_matches = (
        [(m, "auth") for m in auth_matches]
        + [(m, "api_type") for m in api_matches]
        + [(m, "access") for m in access_matches]
        + [(m, "mcp") for m in mcp_matches]
        + [(m, "blocker") for m in blocker_matches]
    )

    for (label, matched_text, context), category in all_matches:
        bundle.keyword_matches.append(
            KeywordMatch(category=category, keyword=label, context=context)
        )

    # ── Store unique labels per category ──
    bundle.detected_auth_methods = get_unique_labels(auth_matches)
    bundle.detected_api_types = get_unique_labels(api_matches)
    bundle.detected_access_signals = get_unique_labels(access_matches)
    bundle.detected_mcp_signals = get_unique_labels(mcp_matches)

    # ── Extract relevant snippets ──
    bundle.relevant_snippets = _extract_relevant_snippets(
        text, max_snippets=max_snippets, max_length=max_snippet_length
    )

    # ── Score evidence quality ──
    bundle.evidence_quality = _score_evidence_quality(bundle)

    logger.info(
        f"[{discovery.app_name}] Evidence: "
        f"auth={bundle.detected_auth_methods}, "
        f"api={bundle.detected_api_types}, "
        f"access={bundle.detected_access_signals}, "
        f"mcp={bundle.detected_mcp_signals}, "
        f"quality={bundle.evidence_quality}"
    )

    return bundle


def _extract_relevant_snippets(
    text: str, max_snippets: int = 5, max_length: int = 500
) -> list[str]:
    """Extract the most relevant text snippets.

    Splits text into paragraphs and scores each by relevance
    (keyword density). Returns top N snippets.
    """
    # Split into paragraphs
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 30]

    if not paragraphs:
        return [text[:max_length]] if text else []

    # Score each paragraph by keyword relevance
    relevance_keywords = [
        "api", "auth", "oauth", "key", "token", "rest", "graphql",
        "endpoint", "developer", "integration", "webhook", "sdk",
        "documentation", "access", "enterprise", "self-serve",
        "mcp", "protocol", "toolkit",
    ]

    scored: list[tuple[float, str]] = []
    for para in paragraphs:
        para_lower = para.lower()
        score = sum(1 for kw in relevance_keywords if kw in para_lower)
        # Boost paragraphs that mention auth or API specifics
        if any(w in para_lower for w in ["oauth", "api key", "bearer", "graphql"]):
            score += 3
        scored.append((score, para))

    # Sort by relevance, take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    snippets = []
    for _, para in scored[:max_snippets]:
        truncated = para[:max_length]
        if len(para) > max_length:
            truncated = truncated.rsplit(" ", 1)[0] + "..."
        snippets.append(truncated)

    return snippets


def _score_evidence_quality(bundle: EvidenceBundle) -> str:
    """Score the overall evidence quality for this bundle."""
    score = 0

    if bundle.has_documentation:
        score += 1

    if bundle.detected_auth_methods:
        score += 1

    if bundle.detected_api_types:
        score += 1

    if bundle.detected_access_signals:
        score += 1

    if len(bundle.relevant_snippets) >= 3:
        score += 1

    if score >= 4:
        return "high"
    elif score >= 2:
        return "medium"
    elif score >= 1:
        return "low"
    return "none"


def _best_url(discovery: DiscoveryResult) -> str:
    """Get the best (most content-rich) URL from discovery results."""
    successful = [p for p in discovery.pages if p.fetch_success]
    if not successful:
        return ""
    # Return the page with the most content
    return max(successful, key=lambda p: p.content_length).url


def bundle_to_llm_prompt(bundle: EvidenceBundle) -> str:
    """Convert an evidence bundle into a compact text prompt for the LLM.

    This is what actually gets sent to the model — never full doc pages.
    Keeps token usage minimal while providing sufficient context.
    """
    parts = [
        f"App: {bundle.app_name}",
        f"Category: {bundle.category_name}",
        f"Hint: {bundle.hint}",
        f"Documentation Found: {'Yes' if bundle.has_documentation else 'No'}",
    ]

    if bundle.docs_url:
        parts.append(f"Docs URL: {bundle.docs_url}")

    if bundle.detected_auth_methods:
        parts.append(f"Detected Auth Methods: {', '.join(bundle.detected_auth_methods)}")

    if bundle.detected_api_types:
        parts.append(f"Detected API Types: {', '.join(bundle.detected_api_types)}")

    if bundle.detected_access_signals:
        parts.append(f"Detected Access Signals: {', '.join(bundle.detected_access_signals)}")

    if bundle.detected_mcp_signals:
        parts.append(f"Detected MCP Signals: {', '.join(bundle.detected_mcp_signals)}")

    if bundle.relevant_snippets:
        parts.append("\n--- Relevant Documentation Excerpts ---")
        for i, snippet in enumerate(bundle.relevant_snippets, 1):
            parts.append(f"\n[Excerpt {i}]:\n{snippet}")

    return "\n".join(parts)
