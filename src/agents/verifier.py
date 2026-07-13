"""Verification Agent — Independent verification using Qwen3-32B via Groq.

A model must NEVER verify its own output. This agent uses a completely
different model to independently assess the primary classification.
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
    EvidenceBundle,
    FieldVerification,
    ResearchResult,
    VerificationResult,
)
from src.agents.prompts import VERIFICATION_SYSTEM_PROMPT, build_verification_prompt

logger = logging.getLogger(__name__)


def _get_groq_client() -> AsyncGroq:
    """Create a Groq client instance."""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY not set.")
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
        f"Verify retry {retry_state.attempt_number}/{settings.max_retries}"
    ),
)
async def _call_verification(client: AsyncGroq, user_prompt: str) -> str:
    """Make the verification API call."""
    try:
        response = await client.chat.completions.create(
            model=settings.verification_model,
            messages=[
                {"role": "system", "content": VERIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.verification_temperature,
            max_tokens=settings.max_tokens,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""
    except RateLimitError as e:
        retry_after = e.response.headers.get("retry-after")
        if retry_after:
            delay = float(retry_after)
            logger.warning(f"Rate limited on Verifier. Sleeping for {delay}s based on header...")
            await asyncio.sleep(delay)
        raise e


async def verify_app(
    bundle: EvidenceBundle,
    classification: ResearchResult,
    client: AsyncGroq | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> VerificationResult:
    """Verify a single app's classification using the verification model."""
    if client is None:
        client = _get_groq_client()

    evidence_text = bundle_to_llm_prompt(bundle)

    classification_summary = json.dumps({
        "auth_method": classification.auth_method.value,
        "access_model": classification.access_model.value,
        "api_type": classification.api_type.value,
        "has_mcp": classification.has_mcp,
        "build_verdict": classification.build_verdict.value,
        "main_blocker": classification.main_blocker,
        "one_line_description": classification.one_line_description,
    }, indent=2)

    user_prompt = build_verification_prompt(evidence_text, classification_summary)

    async def _do_work():
        logger.info(f"[{bundle.app_name}] Verifying with {settings.verification_model}")

        try:
            raw_response = await _call_verification(client, user_prompt)
            parsed = json.loads(raw_response)

            field_assessments = parsed.get("field_assessments", {})
            field_verifications: list[FieldVerification] = []
            disagreements: list[str] = []

            primary_values = {
                "auth_method": classification.auth_method.value,
                "access_model": classification.access_model.value,
                "api_type": classification.api_type.value,
                "has_mcp": str(classification.has_mcp),
                "build_verdict": classification.build_verdict.value,
                "main_blocker": classification.main_blocker,
            }

            for field_name, primary_value in primary_values.items():
                assessment = field_assessments.get(field_name, {})
                agrees = assessment.get("agree", True)
                confidence = min(1.0, max(0.0, float(assessment.get("confidence", 0.5))))
                suggested = str(assessment.get("suggested_value", primary_value))
                reasoning = assessment.get("reasoning", "")

                fv = FieldVerification(
                    field_name=field_name,
                    primary_value=primary_value,
                    verified_value=suggested if not agrees else primary_value,
                    agrees=agrees,
                    confidence=confidence,
                    reasoning=reasoning,
                )
                field_verifications.append(fv)

                if not agrees:
                    disagreements.append(
                        f"{field_name}: primary='{primary_value}' vs verified='{suggested}'"
                    )

            overall_confidence = min(
                1.0,
                max(0.0, float(parsed.get("overall_confidence", 0.5)))
            )

            needs_review = (
                overall_confidence < settings.human_audit_threshold
                or len(disagreements) >= 3
            )

            result = VerificationResult(
                app_id=bundle.app_id,
                app_name=bundle.app_name,
                field_verifications=field_verifications,
                overall_confidence=overall_confidence,
                disagreements=disagreements,
                verification_reasoning=parsed.get("overall_reasoning", ""),
                needs_human_review=needs_review,
            )

            status = "⚠️" if disagreements else "✓"
            logger.info(
                f"[{bundle.app_name}] {status} Verified: confidence={overall_confidence:.2f}, "
                f"disagreements={len(disagreements)}, needs_review={needs_review}"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"[{bundle.app_name}] Verification JSON parse failed: {e}")
            return _fallback_verification(bundle.app_id, bundle.app_name, str(e))
        except Exception as e:
            logger.error(f"[{bundle.app_name}] Verification failed: {e}")
            return _fallback_verification(bundle.app_id, bundle.app_name, str(e))

    if semaphore:
        async with semaphore:
            return await _do_work()
    else:
        return await _do_work()


async def verify_batch(
    bundles: list[EvidenceBundle],
    classifications: list[ResearchResult],
    client: AsyncGroq | None = None,
) -> list[VerificationResult]:
    """Verify a batch of classifications asynchronously with strict concurrency limits."""
    if client is None:
        client = _get_groq_client()

    class_by_id = {c.app_id: c for c in classifications}
    
    # Qwen has 60 RPM limit, so concurrency of 5 is safe
    semaphore = asyncio.Semaphore(5)
    
    tasks = []
    for bundle in bundles:
        classification = class_by_id.get(bundle.app_id)
        if not classification:
            logger.warning(f"No classification found for app {bundle.app_name}")
            # Use asyncio.sleep(0) to wrap synchronous fallback into an awaitable task easily
            async def _fake_task(app_id, app_name):
                return _fallback_verification(app_id, app_name, "No classification")
            tasks.append(_fake_task(bundle.app_id, bundle.app_name))
            continue
            
        tasks.append(verify_app(bundle, classification, client, semaphore))
        
    return await asyncio.gather(*tasks)


def resolve_disagreements(
    classification: ResearchResult,
    verification: VerificationResult,
) -> ResearchResult:
    """Resolve disagreements between primary and verification models.

    Strategy:
    - If verifier agrees: keep primary value
    - If verifier disagrees with high confidence (>0.7): use verifier's value
    - If verifier disagrees with low confidence: keep primary, flag for review
    """
    resolved = classification.model_copy()

    for fv in verification.field_verifications:
        if fv.agrees:
            continue

        # Only override if verifier is confident
        if fv.confidence >= 0.7:
            # Lazy load to avoid circular dependency during module initialization
            if fv.field_name == "auth_method":
                from src.agents.classifier import _parse_auth_method
                resolved.auth_method = _parse_auth_method(fv.verified_value)
            elif fv.field_name == "access_model":
                from src.agents.classifier import _parse_access_model
                resolved.access_model = _parse_access_model(fv.verified_value)
            elif fv.field_name == "api_type":
                from src.agents.classifier import _parse_api_type
                resolved.api_type = _parse_api_type(fv.verified_value)
            elif fv.field_name == "has_mcp":
                resolved.has_mcp = fv.verified_value.lower() == "true"
            elif fv.field_name == "build_verdict":
                from src.agents.classifier import _parse_build_verdict
                resolved.build_verdict = _parse_build_verdict(fv.verified_value)
            elif fv.field_name == "main_blocker":
                resolved.main_blocker = fv.verified_value

            logger.info(
                f"[{classification.app_name}] Resolved {fv.field_name}: "
                f"'{fv.primary_value}' → '{fv.verified_value}' (confidence={fv.confidence:.2f})"
            )

    return resolved


def _fallback_verification(
    app_id: int, app_name: str, error: str
) -> VerificationResult:
    """Create a fallback verification result when verification fails."""
    return VerificationResult(
        app_id=app_id,
        app_name=app_name,
        overall_confidence=0.3,
        needs_human_review=True,
        verification_reasoning=f"Verification failed: {error[:100]}",
    )
