"""Centralized configuration for the research pipeline.

All configurable values live here. No magic constants elsewhere.
Uses pydantic-settings for validation and .env loading.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Groq API ---
    groq_api_key: str = ""

    # --- Model Configuration ---
    primary_model: str = "openai/gpt-oss-120b"
    verification_model: str = "qwen/qwen3-32b"
    primary_temperature: float = 0.1
    verification_temperature: float = 0.1
    max_tokens: int = 2048

    # --- Rate Limiting ---
    max_rpm: int = 25  # Requests per minute (conservative for free tier)
    request_delay_seconds: float = 2.5  # Delay between requests
    max_retries: int = 15
    retry_base_delay: float = 2.0  # Base delay for exponential backoff

    # --- Web Crawling ---
    crawl_timeout_seconds: int = 15
    max_concurrent_crawls: int = 5
    user_agent: str = (
        "Mozilla/5.0 (compatible; ComposioResearchBot/1.0; +https://composio.dev)"
    )

    # --- Evidence Extraction ---
    max_snippet_length: int = 500  # Max chars per snippet
    max_snippets_per_app: int = 5  # Max relevant snippets to keep
    max_evidence_tokens: int = 800  # Max tokens in evidence bundle for LLM

    # --- Human Audit ---
    audit_sample_size: int = 30  # 3 per category
    audit_per_category: int = 3

    # --- Confidence Thresholds ---
    confidence_high: float = 0.8
    confidence_medium: float = 0.6
    confidence_low: float = 0.4
    human_audit_threshold: float = 0.6  # Below this → flag for audit

    # --- File Paths ---
    data_dir: Path = PROJECT_ROOT / "data"
    output_dir: Path = PROJECT_ROOT / "output"

    # Input
    app_seeds_file: str = "app_seeds.json"

    # Intermediate outputs
    discovery_results_file: str = "discovery_results.json"
    evidence_bundles_file: str = "evidence_bundles.json"
    classification_results_file: str = "classification_results.json"
    verification_results_file: str = "verification_results.json"
    composio_toolkits_file: str = "composio_toolkits.json"

    # Audit
    audit_worksheet_file: str = "audit_worksheet.json"
    audit_results_file: str = "audit_results.json"
    learned_url_patterns_file: str = "learned_url_patterns.json"

    # Final outputs
    final_dataset_json: str = "final_dataset.json"
    final_dataset_csv: str = "final_dataset.csv"
    html_report_file: str = "composio_research_report.html"

    # --- Composio Opportunity Scoring ---
    score_self_serve: int = 3
    score_oauth_apikey: int = 2
    score_rest_api: int = 2
    score_public_docs: int = 2
    score_mcp_available: int = 1
    score_enterprise_gated: int = -3
    score_no_public_api: int = -5

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # --- Derived Paths ---
    def get_data_path(self, filename: str) -> Path:
        """Get full path for a data file."""
        return self.data_dir / filename

    def get_output_path(self, filename: str) -> Path:
        """Get full path for an output file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir / filename


# Singleton instance
settings = Settings()
