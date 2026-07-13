"""Centralized keyword patterns for deterministic extraction.

These patterns are the first line of analysis — they run BEFORE any LLM call.
They extract auth methods, API types, access models, and MCP signals
from raw documentation text using regex.
"""

import re
from dataclasses import dataclass, field


@dataclass
class PatternGroup:
    """A group of regex patterns for detecting a specific signal."""
    category: str
    patterns: list[re.Pattern] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)

    def find_matches(self, text: str) -> list[tuple[str, str]]:
        """Find all pattern matches in text. Returns (label, matched_text) pairs."""
        matches = []
        text_lower = text.lower()
        for pattern, label in zip(self.patterns, self.labels):
            found = pattern.search(text_lower)
            if found:
                matches.append((label, found.group(0)))
        return matches

    def find_matches_with_context(
        self, text: str, context_chars: int = 80
    ) -> list[tuple[str, str, str]]:
        """Find matches with surrounding context. Returns (label, match, context)."""
        matches = []
        text_lower = text.lower()
        for pattern, label in zip(self.patterns, self.labels):
            for found in pattern.finditer(text_lower):
                start = max(0, found.start() - context_chars)
                end = min(len(text), found.end() + context_chars)
                context = text[start:end].strip()
                matches.append((label, found.group(0), context))
        return matches


# ─── Authentication Patterns ─────────────────────────────────────────────────

AUTH_PATTERNS = PatternGroup(
    category="auth",
    patterns=[
        re.compile(r"\boauth\s*2\.?0?\b", re.IGNORECASE),
        re.compile(r"\boauth\b", re.IGNORECASE),
        re.compile(r"\bapi[_\s-]?key\b", re.IGNORECASE),
        re.compile(r"\bbearer\s+token\b", re.IGNORECASE),
        re.compile(r"\bbasic\s+auth(?:entication)?\b", re.IGNORECASE),
        re.compile(r"\bjwt\b", re.IGNORECASE),
        re.compile(r"\bjson\s+web\s+token\b", re.IGNORECASE),
        re.compile(r"\bsaml\b", re.IGNORECASE),
        re.compile(r"\bsso\b", re.IGNORECASE),
        re.compile(r"\bpersonal\s+access\s+token\b", re.IGNORECASE),
        re.compile(r"\bservice\s+account\b", re.IGNORECASE),
        re.compile(r"\bclient[_\s]?credentials\b", re.IGNORECASE),
        re.compile(r"\bauthorization\s+code\b", re.IGNORECASE),
        re.compile(r"\bhmac\b", re.IGNORECASE),
        re.compile(r"\bwebhook\s+secret\b", re.IGNORECASE),
    ],
    labels=[
        "OAuth2", "OAuth", "API Key", "Bearer Token", "Basic Auth",
        "JWT", "JWT", "SAML", "SSO", "Personal Access Token",
        "Service Account", "Client Credentials", "Authorization Code",
        "HMAC", "Webhook Secret",
    ],
)

# ─── API Type Patterns ───────────────────────────────────────────────────────

API_TYPE_PATTERNS = PatternGroup(
    category="api_type",
    patterns=[
        re.compile(r"\brest\s*(?:ful)?\s*api\b", re.IGNORECASE),
        re.compile(r"\bgraphql\b", re.IGNORECASE),
        re.compile(r"\bgrpc\b", re.IGNORECASE),
        re.compile(r"\bwebsocket\b", re.IGNORECASE),
        re.compile(r"\bsoap\b", re.IGNORECASE),
        re.compile(r"\bopenapi\b", re.IGNORECASE),
        re.compile(r"\bswagger\b", re.IGNORECASE),
        re.compile(r"\b(?:get|post|put|patch|delete)\s+/\w+", re.IGNORECASE),
        re.compile(r"\bendpoint\b", re.IGNORECASE),
    ],
    labels=[
        "REST", "GraphQL", "gRPC", "WebSocket", "SOAP",
        "REST", "REST", "REST", "REST",
    ],
)

# ─── Access Model Patterns ───────────────────────────────────────────────────

ACCESS_PATTERNS = PatternGroup(
    category="access",
    patterns=[
        re.compile(r"\bfree\s+(?:tier|plan|trial)\b", re.IGNORECASE),
        re.compile(r"\bsign\s+up\b", re.IGNORECASE),
        re.compile(r"\bself[_\s-]?serv(?:e|ice)\b", re.IGNORECASE),
        re.compile(r"\bdeveloper\s+(?:portal|access|account|console)\b", re.IGNORECASE),
        re.compile(r"\bcontact\s+(?:sales|us)\b", re.IGNORECASE),
        re.compile(r"\benterprise\s+(?:plan|only|tier|access)\b", re.IGNORECASE),
        re.compile(r"\brequest\s+access\b", re.IGNORECASE),
        re.compile(r"\bpartner[_\s-]?(?:only|program|access)\b", re.IGNORECASE),
        re.compile(r"\binvite[_\s-]?only\b", re.IGNORECASE),
        re.compile(r"\bwaitlist\b", re.IGNORECASE),
        re.compile(r"\bbeta\s+access\b", re.IGNORECASE),
        re.compile(r"\bopen[_\s-]?source\b", re.IGNORECASE),
        re.compile(r"\bgithub\.com/[\w-]+/[\w-]+\b", re.IGNORECASE),
    ],
    labels=[
        "Free Tier", "Sign Up", "Self-Serve", "Developer Portal",
        "Contact Sales", "Enterprise Only", "Request Access",
        "Partner Only", "Invite Only", "Waitlist", "Beta Access",
        "Open Source", "Open Source",
    ],
)

# ─── MCP Patterns ────────────────────────────────────────────────────────────

MCP_PATTERNS = PatternGroup(
    category="mcp",
    patterns=[
        re.compile(r"\bmcp\b", re.IGNORECASE),
        re.compile(r"\bmodel\s+context\s+protocol\b", re.IGNORECASE),
        re.compile(r"\bmcp[_\s-]?server\b", re.IGNORECASE),
        re.compile(r"\bmcp[_\s-]?client\b", re.IGNORECASE),
        re.compile(r"\banthropic.*mcp\b", re.IGNORECASE),
    ],
    labels=[
        "MCP", "Model Context Protocol", "MCP Server", "MCP Client", "MCP",
    ],
)

# ─── Blocker Patterns ────────────────────────────────────────────────────────

BLOCKER_PATTERNS = PatternGroup(
    category="blocker",
    patterns=[
        re.compile(r"\bno\s+(?:public\s+)?api\b", re.IGNORECASE),
        re.compile(r"\bapi\s+(?:is\s+)?deprecated\b", re.IGNORECASE),
        re.compile(r"\benterprise\s+(?:approval|required)\b", re.IGNORECASE),
        re.compile(r"\bpartner[_\s-]?only\b", re.IGNORECASE),
        re.compile(r"\blimited\s+(?:access|documentation)\b", re.IGNORECASE),
        re.compile(r"\bprivate\s+(?:api|beta)\b", re.IGNORECASE),
        re.compile(r"\bcoming\s+soon\b", re.IGNORECASE),
        re.compile(r"\bnda\s+required\b", re.IGNORECASE),
        re.compile(r"\brate\s+limit(?:ed|ing|s)?\b", re.IGNORECASE),
    ],
    labels=[
        "No Public API", "Deprecated API", "Enterprise Approval",
        "Partner Only", "Limited Docs", "Private API",
        "Coming Soon", "NDA Required", "Rate Limited",
    ],
)

# ─── Utility Functions ───────────────────────────────────────────────────────


def extract_all_signals(text: str) -> dict[str, list[tuple[str, str, str]]]:
    """Run all pattern groups against text. Returns dict of category → matches."""
    return {
        "auth": AUTH_PATTERNS.find_matches_with_context(text),
        "api_type": API_TYPE_PATTERNS.find_matches_with_context(text),
        "access": ACCESS_PATTERNS.find_matches_with_context(text),
        "mcp": MCP_PATTERNS.find_matches_with_context(text),
        "blocker": BLOCKER_PATTERNS.find_matches_with_context(text),
    }


def get_unique_labels(matches: list[tuple[str, str, str]]) -> list[str]:
    """Extract unique labels from match results, preserving order."""
    seen = set()
    result = []
    for label, _, _ in matches:
        if label not in seen:
            seen.add(label)
            result.append(label)
    return result
