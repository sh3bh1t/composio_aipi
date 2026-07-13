"""Learned URL Patterns Registry.

Maintains a running set of URL path patterns extracted from:
1. The hardcoded patterns in doc_discovery.py (baseline)
2. Human-provided URLs from audit_worksheet.json (additive)

Each audit cycle enriches the pattern set. Patterns are never removed,
only added, so future discovery runs benefit from all prior human insights.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from src.config import settings

logger = logging.getLogger(__name__)


def extract_patterns_from_urls(urls: list[str]) -> set[str]:
    """Extract reusable URL path patterns from concrete URLs.

    For example:
        https://developers.hubspot.com/docs -> "developers.{domain}/docs"
        https://dev.frontapp.com/reference/introduction -> "dev.{domain}/reference"
        https://developer.salesforce.com/docs -> "developer.{domain}/docs"
    """
    patterns: set[str] = set()

    for url in urls:
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                continue

            host_parts = parsed.netloc.split(".")
            if len(host_parts) < 3:
                path = parsed.path.strip("/")
                if path:
                    first_segment = path.split("/")[0]
                    patterns.add(f"{{domain}}/{first_segment}")
                continue

            subdomain = host_parts[0]
            path = parsed.path.strip("/")
            if path:
                first_segment = path.split("/")[0]
                patterns.add(f"{subdomain}.{{domain}}/{first_segment}")
            else:
                patterns.add(f"{subdomain}.{{domain}}")

        except Exception:
            continue

    return patterns


def load_learned_patterns() -> dict:
    """Load the learned URL patterns from disk."""
    patterns_path = settings.get_data_path(settings.learned_url_patterns_file)
    if patterns_path.exists():
        with open(patterns_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"patterns": [], "source_urls": []}


def save_learned_patterns(data: dict) -> None:
    """Save learned URL patterns to disk."""
    patterns_path = settings.get_data_path(settings.learned_url_patterns_file)
    patterns_path.parent.mkdir(parents=True, exist_ok=True)
    with open(patterns_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(data['patterns'])} learned URL patterns to {patterns_path}")


def update_patterns_from_audit(audit_worksheet_path: Path) -> dict:
    """Extract new URL patterns from human_urls in the audit worksheet
    and merge them into the running patterns set.

    Returns the updated patterns data.
    """
    data = load_learned_patterns()
    existing_patterns = set(data.get("patterns", []))
    existing_source_urls = set(data.get("source_urls", []))

    if not audit_worksheet_path.exists():
        logger.warning("No audit worksheet found, skipping URL pattern learning")
        return data

    with open(audit_worksheet_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    new_urls: list[str] = []
    for record in records:
        human_urls = record.get("human_urls", [])
        for url in human_urls:
            if url and url not in existing_source_urls:
                new_urls.append(url)
                existing_source_urls.add(url)

    if new_urls:
        new_patterns = extract_patterns_from_urls(new_urls)
        added = new_patterns - existing_patterns
        existing_patterns.update(new_patterns)
        if added:
            logger.info(f"Learned {len(added)} new URL patterns from audit: {added}")

    data = {
        "patterns": sorted(existing_patterns),
        "source_urls": sorted(existing_source_urls),
    }
    save_learned_patterns(data)
    return data


def get_additional_urls_for_domain(base_domain: str) -> list[str]:
    """Generate additional candidate URLs for a domain using learned patterns.

    Returns a list of concrete URLs by applying learned patterns to the domain.
    """
    data = load_learned_patterns()
    patterns = data.get("patterns", [])

    urls: list[str] = []
    for pattern in patterns:
        try:
            concrete = pattern.replace("{domain}", base_domain)
            url = f"https://{concrete}"
            urls.append(url)
        except Exception:
            continue

    return urls
