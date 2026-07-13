"""Classification Agent — Primary LLM classifier using GPT-OSS-120B via Groq.

Takes an EvidenceBundle, converts it to a compact prompt, sends to LLM,
and parses the structured JSON response into a ResearchResult.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from groq import AsyncGroq, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import settings
from src.extraction.evidence_builder import bundle_to_llm_prompt
from src.models import (
    AuthMethod,
    APIType,
    AccessModel,
    BuildVerdict,
    EvidenceBundle,
    ResearchResult,
)
from src.agents.prompts import CLASSIFICATION_SYSTEM_PROMPT, build_classification_prompt

logger = logging.getLogger(__name__)


def _get_groq_client() -> AsyncGroq:
    """Create a Groq client instance."""
    if not settings.groq_api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Copy .env.example to .env and add your key."
        )
    return AsyncGroq(api_key=settings.groq_api_key, max_retries=2)


@retry(
    stop=stop_after_attempt(settings.max_retries),
    wait=wait_exponential(
        multiplier=settings.retry_base_delay,
        min=settings.retry_base_delay,
        max=60,
    ),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda retry_state: logger.warning(
        f"Retry {retry_state.attempt_number}/{settings.max_retries} "
        f"after error: {retry_state.outcome.exception()}"
    ),
)
async def _call_groq(
    client: AsyncGroq,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
) -> str:
    """Make a Groq API call with retry logic."""
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=settings.max_tokens,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""
    except RateLimitError as e:
        # Check for retry-after header
        retry_after = e.response.headers.get("retry-after")
        if retry_after:
            delay = float(retry_after)
            logger.warning(f"Rate limited. Sleeping for {delay} seconds based on header...")
            await asyncio.sleep(delay)
        raise e


def _parse_auth_method(value: str) -> AuthMethod:
    """Parse auth method string to enum, with fuzzy matching."""
    value_lower = value.lower().strip()
    mapping = {
        "oauth2": AuthMethod.OAUTH2,
        "oauth 2": AuthMethod.OAUTH2,
        "oauth": AuthMethod.OAUTH2,
        "api key": AuthMethod.API_KEY,
        "api_key": AuthMethod.API_KEY,
        "apikey": AuthMethod.API_KEY,
        "bearer token": AuthMethod.BEARER_TOKEN,
        "bearer": AuthMethod.BEARER_TOKEN,
        "basic auth": AuthMethod.BASIC_AUTH,
        "basic authentication": AuthMethod.BASIC_AUTH,
        "jwt": AuthMethod.JWT,
        "mixed": AuthMethod.MIXED,
        "none": AuthMethod.NONE,
    }
    return mapping.get(value_lower, AuthMethod.UNKNOWN)


def _parse_api_type(value: str) -> APIType:
    """Parse API type string to enum."""
    value_lower = value.lower().strip()
    mapping = {
        "rest": APIType.REST,
        "restful": APIType.REST,
        "graphql": APIType.GRAPHQL,
        "grpc": APIType.GRPC,
        "websocket": APIType.WEBSOCKET,
        "mixed": APIType.MIXED,
        "cli only": APIType.CLI_ONLY,
        "cli": APIType.CLI_ONLY,
        "none": APIType.NONE,
    }
    return mapping.get(value_lower, APIType.UNKNOWN)


def _parse_access_model(value: str) -> AccessModel:
    """Parse access model string to enum."""
    value_lower = value.lower().strip()
    mapping = {
        "self-serve": AccessModel.SELF_SERVE,
        "self serve": AccessModel.SELF_SERVE,
        "self_serve": AccessModel.SELF_SERVE,
        "gated": AccessModel.GATED,
        "freemium": AccessModel.FREEMIUM,
        "open source": AccessModel.OPEN_SOURCE,
        "open-source": AccessModel.OPEN_SOURCE,
        "opensource": AccessModel.OPEN_SOURCE,
    }
    return mapping.get(value_lower, AccessModel.UNKNOWN)


def _parse_build_verdict(value: str) -> BuildVerdict:
    """Parse build verdict string to enum."""
    value_lower = value.lower().strip()
    mapping = {
        "easy": BuildVerdict.EASY,
        "moderate": BuildVerdict.MODERATE,
        "hard": BuildVerdict.HARD,
        "not feasible": BuildVerdict.NOT_FEASIBLE,
        "not_feasible": BuildVerdict.NOT_FEASIBLE,
    }
    return mapping.get(value_lower, BuildVerdict.UNKNOWN)


async def classify_app(
    bundle: EvidenceBundle,
    client: AsyncGroq | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> ResearchResult:
    """Classify a single app using the primary LLM."""
    if client is None:
        client = _get_groq_client()

    evidence_text = bundle_to_llm_prompt(bundle)
    user_prompt = build_classification_prompt(evidence_text)

    async def _do_work():
        logger.info(f"[{bundle.app_name}] Sending to {settings.primary_model} for classification")
        try:
            raw_response = await _call_groq(
                client=client,
                system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model=settings.primary_model,
                temperature=settings.primary_temperature,
            )

            parsed = json.loads(raw_response)

            result = ResearchResult(
                app_id=bundle.app_id,
                app_name=bundle.app_name,
                category=bundle.category_name,
                one_line_description=parsed.get("one_line_description", ""),
                auth_method=_parse_auth_method(parsed.get("auth_method", "Unknown")),
                access_model=_parse_access_model(parsed.get("access_model", "Unknown")),
                api_type=_parse_api_type(parsed.get("api_type", "Unknown")),
                has_mcp=parsed.get("has_mcp", False),
                mcp_details=parsed.get("mcp_details", ""),
                build_verdict=_parse_build_verdict(parsed.get("build_verdict", "Unknown")),
                main_blocker=parsed.get("main_blocker", ""),
                evidence_urls=parsed.get("evidence_urls", []),
                llm_reasoning=parsed.get("reasoning", ""),
                raw_llm_response=raw_response,
            )

            if not result.evidence_urls and bundle.docs_url:
                result.evidence_urls = [bundle.docs_url]

            logger.info(f"[{bundle.app_name}] Classified: {result.auth_method.value}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"[{bundle.app_name}] Failed to parse LLM JSON: {e}")
            return _fallback_result(bundle, str(e))
        except Exception as e:
            logger.error(f"[{bundle.app_name}] Classification failed: {e}")
            return _fallback_result(bundle, str(e))

    if semaphore:
        async with semaphore:
            return await _do_work()
    else:
        return await _do_work()


async def classify_batch(
    bundles: list[EvidenceBundle],
    client: AsyncGroq | None = None,
) -> list[ResearchResult]:
    """Classify a batch of apps asynchronously with strict concurrency limits."""
    if client is None:
        client = _get_groq_client()

    # Max 3 concurrent to stay safe with 30 RPM limit on free tier
    semaphore = asyncio.Semaphore(3)
    
    tasks = [
        classify_app(bundle, client, semaphore)
        for bundle in bundles
    ]
    
    return await asyncio.gather(*tasks)


def _fallback_result(bundle: EvidenceBundle, error: str) -> ResearchResult:
    """Create a fallback result when classification fails."""
    return ResearchResult(
        app_id=bundle.app_id,
        app_name=bundle.app_name,
        category=bundle.category_name,
        one_line_description=f"Classification failed: {error[:50]}",
        main_blocker=f"Classification error: {error[:100]}",
    )
