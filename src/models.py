"""Pydantic data models for the entire research pipeline.

Single source of truth for all structured data flowing through the system.
Every stage reads and writes these models — no ad-hoc dicts.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────


class AuthMethod(str, Enum):
    """Authentication methods for API access."""
    OAUTH2 = "OAuth2"
    API_KEY = "API Key"
    BEARER_TOKEN = "Bearer Token"
    BASIC_AUTH = "Basic Auth"
    JWT = "JWT"
    MIXED = "Mixed"
    NONE = "None"
    UNKNOWN = "Unknown"


class APIType(str, Enum):
    """API surface types."""
    REST = "REST"
    GRAPHQL = "GraphQL"
    GRPC = "gRPC"
    WEBSOCKET = "WebSocket"
    MIXED = "Mixed"
    CLI_ONLY = "CLI Only"
    NONE = "None"
    UNKNOWN = "Unknown"


class AccessModel(str, Enum):
    """Whether the API is self-serve or gated."""
    SELF_SERVE = "Self-Serve"
    GATED = "Gated"
    FREEMIUM = "Freemium"
    OPEN_SOURCE = "Open Source"
    UNKNOWN = "Unknown"


class BuildVerdict(str, Enum):
    """Whether a Composio toolkit is buildable."""
    EASY = "Easy"
    MODERATE = "Moderate"
    HARD = "Hard"
    NOT_FEASIBLE = "Not Feasible"
    UNKNOWN = "Unknown"


class OpportunityLevel(str, Enum):
    """Composio integration opportunity level."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ConfidenceLevel(str, Enum):
    """Confidence level for a classification."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    NEEDS_REVIEW = "Needs Review"


# ─── Input Models ─────────────────────────────────────────────────────────────


class AppSeed(BaseModel):
    """Single app from app_seeds.json."""
    id: int
    name: str
    hint: str
    category_id: int = 0
    category_name: str = ""


# ─── Discovery Models ────────────────────────────────────────────────────────


class DiscoveredPage(BaseModel):
    """A single discovered documentation page."""
    url: str
    title: str = ""
    content_preview: str = ""  # First ~200 chars
    content_length: int = 0
    fetch_success: bool = True
    error: str = ""


class DiscoveryResult(BaseModel):
    """Documentation discovery output for one app."""
    app_id: int
    app_name: str
    hint: str
    pages: list[DiscoveredPage] = Field(default_factory=list)
    raw_text: str = ""  # Combined text from all pages
    discovery_success: bool = False
    total_pages_found: int = 0
    total_content_length: int = 0


# ─── Evidence Models ─────────────────────────────────────────────────────────


class KeywordMatch(BaseModel):
    """A keyword pattern match found in documentation."""
    category: str  # e.g., "auth", "api_type", "access"
    keyword: str  # The matched keyword
    context: str = ""  # Surrounding text (50 chars each side)


class EvidenceBundle(BaseModel):
    """Compact evidence bundle sent to LLM for classification.

    This is the bridge between deterministic extraction and LLM reasoning.
    Contains only the relevant snippets — never full doc pages.
    """
    app_id: int
    app_name: str
    hint: str
    category_name: str

    # Deterministic extractions
    keyword_matches: list[KeywordMatch] = Field(default_factory=list)
    detected_auth_methods: list[str] = Field(default_factory=list)
    detected_api_types: list[str] = Field(default_factory=list)
    detected_access_signals: list[str] = Field(default_factory=list)
    detected_mcp_signals: list[str] = Field(default_factory=list)

    # Relevant snippets (compact)
    relevant_snippets: list[str] = Field(default_factory=list)

    # Evidence quality indicators
    has_documentation: bool = False
    docs_url: str = ""
    evidence_quality: str = "none"  # none, low, medium, high


# ─── Classification Models ───────────────────────────────────────────────────


class ResearchResult(BaseModel):
    """Primary LLM classification output for one app."""
    app_id: int
    app_name: str
    category: str

    # Core fields
    one_line_description: str = ""
    auth_method: AuthMethod = AuthMethod.UNKNOWN
    access_model: AccessModel = AccessModel.UNKNOWN
    api_type: APIType = APIType.UNKNOWN
    has_mcp: bool = False
    mcp_details: str = ""
    build_verdict: BuildVerdict = BuildVerdict.UNKNOWN
    main_blocker: str = ""
    evidence_urls: list[str] = Field(default_factory=list)

    # Metadata
    llm_reasoning: str = ""
    raw_llm_response: str = ""


# ─── Verification Models ─────────────────────────────────────────────────────


class FieldVerification(BaseModel):
    """Verification result for a single field."""
    field_name: str
    primary_value: str
    verified_value: str
    agrees: bool = True
    confidence: float = 0.5
    reasoning: str = ""


class VerificationResult(BaseModel):
    """Verification agent output for one app."""
    app_id: int
    app_name: str

    field_verifications: list[FieldVerification] = Field(default_factory=list)
    overall_confidence: float = 0.5
    disagreements: list[str] = Field(default_factory=list)
    verification_reasoning: str = ""
    needs_human_review: bool = False


# ─── Confidence & Audit Models ───────────────────────────────────────────────


class ConfidenceScore(BaseModel):
    """Composite confidence score for one app."""
    app_id: int
    evidence_score: float = 0.0  # 0-0.2: docs found?
    deterministic_score: float = 0.0  # 0-0.2: keyword matches?
    agreement_score: float = 0.0  # 0-0.3: models agree?
    quality_score: float = 0.0  # 0-0.3: evidence quality
    total_score: float = 0.0  # 0-1.0
    level: ConfidenceLevel = ConfidenceLevel.NEEDS_REVIEW


class AuditRecord(BaseModel):
    """Human audit record for one app."""
    app_id: int
    app_name: str
    category: str

    # Pipeline values (what the system produced)
    pipeline_auth: str = ""
    pipeline_access: str = ""
    pipeline_api_type: str = ""
    pipeline_mcp: bool = False
    pipeline_verdict: str = ""
    pipeline_blocker: str = ""

    # Human-verified values
    human_auth: str = ""
    human_access: str = ""
    human_api_type: str = ""
    human_mcp: bool = False
    human_verdict: str = ""
    human_blocker: str = ""

    # Assessment
    auth_correct: bool = False
    access_correct: bool = False
    api_type_correct: bool = False
    mcp_correct: bool = False
    verdict_correct: bool = False
    blocker_correct: bool = False
    notes: str = ""


# ─── Composio-Specific Models ────────────────────────────────────────────────


class ComposioToolkitInfo(BaseModel):
    """Whether Composio already has a toolkit for this app."""
    app_name: str
    has_toolkit: bool = False
    toolkit_url: str = ""


class OpportunityScore(BaseModel):
    """Composio integration opportunity score for one app."""
    app_id: int
    app_name: str
    category: str

    # Score components
    self_serve_score: int = 0
    auth_score: int = 0
    api_score: int = 0
    docs_score: int = 0
    mcp_score: int = 0
    gated_penalty: int = 0
    no_api_penalty: int = 0

    # Computed
    total_score: int = 0
    level: OpportunityLevel = OpportunityLevel.LOW
    rationale: str = ""

    # Composio context
    composio_has_toolkit: bool = False
    is_new_opportunity: bool = False


# ─── Final Output Models ─────────────────────────────────────────────────────


class FinalAppRecord(BaseModel):
    """Merged final record for one app — the single source of truth."""
    app_id: int
    app_name: str
    category: str
    one_line_description: str = ""

    # Core research fields
    auth_method: str = "Unknown"
    access_model: str = "Unknown"
    api_type: str = "Unknown"
    has_mcp: bool = False
    mcp_details: str = ""
    build_verdict: str = "Unknown"
    main_blocker: str = ""
    evidence_urls: list[str] = Field(default_factory=list)

    # Confidence
    confidence_score: float = 0.0
    confidence_level: str = "Needs Review"

    # Composio context
    composio_has_toolkit: bool = False
    opportunity_score: int = 0
    opportunity_level: str = "Low"

    # Audit (if this app was audited)
    was_audited: bool = False
    audit_corrections: list[str] = Field(default_factory=list)


# ─── Insights Models ─────────────────────────────────────────────────────────


class InsightsSummary(BaseModel):
    """Aggregate insights from the full dataset."""
    total_apps: int = 100

    # Distributions
    auth_distribution: dict[str, int] = Field(default_factory=dict)
    access_distribution: dict[str, int] = Field(default_factory=dict)
    api_type_distribution: dict[str, int] = Field(default_factory=dict)
    mcp_distribution: dict[str, int] = Field(default_factory=dict)
    category_distribution: dict[str, int] = Field(default_factory=dict)
    verdict_distribution: dict[str, int] = Field(default_factory=dict)

    # Rankings
    top_blockers: list[dict[str, int | str]] = Field(default_factory=list)
    top_opportunities: list[dict[str, int | str]] = Field(default_factory=list)

    # Headline metrics
    pct_self_serve: float = 0.0
    pct_gated: float = 0.0
    dominant_auth: str = ""
    pct_mcp_available: float = 0.0
    avg_confidence: float = 0.0
    most_promising_category: str = ""

    # Accuracy (from audit)
    accuracy_before_verification: float = 0.0
    accuracy_after_verification: float = 0.0
    total_corrections: int = 0
    lessons_learned: list[str] = Field(default_factory=list)
