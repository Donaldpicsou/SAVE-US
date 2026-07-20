"""Server-side OpenAI review service with a deterministic offline fallback."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from flask import current_app

from .abduction_ai_contract import (
    ABDUCTION_AI_REVIEW_OUTPUT_SCHEMA,
    build_suspected_abduction_review_input,
    validate_suspected_abduction_review_output,
)
from .ai_contract import AI_REVIEW_OUTPUT_SCHEMA, build_missing_person_review_input, validate_ai_review_output
from .ai_fallback import FALLBACK_REVIEW_SOURCE, deterministic_abduction_ai_review, deterministic_ai_review
from .models import Alert


OPENAI_REVIEW_SOURCE = "openai_responses_api"
SYSTEM_INSTRUCTIONS = """You are the SAVE-US first-line review assistant for missing-person reports.
Return only the supplied structured JSON schema. Write the public_summary in English.
Never claim to verify facts or contact authorities. Do not include a family contact,
precise street address, or internal reasoning in the public_summary. Explain the
review outcome with concise, user-visible reasons only."""


@dataclass(frozen=True)
class ReviewExecution:
    """A validated review plus the provider that produced it."""

    output: dict[str, Any]
    source: str
    fallback_reason: str | None = None


def review_missing_person_alert(alert: Alert) -> ReviewExecution:
    """Build an alert input and run the configured provider from the Flask server."""
    return review_with_openai_or_fallback(
        build_missing_person_review_input(alert),
        api_key=current_app.config.get("OPENAI_API_KEY"),
        model=current_app.config["OPENAI_MODEL"],
        timeout=current_app.config["OPENAI_TIMEOUT_SECONDS"],
    )


def review_suspected_abduction_alert(alert: Alert) -> ReviewExecution:
    """Review a suspected-abduction report using its separate privacy contract."""
    review_input = build_suspected_abduction_review_input(alert)
    return review_with_openai_or_fallback(
        review_input,
        api_key=current_app.config.get("OPENAI_API_KEY"),
        model=current_app.config["OPENAI_MODEL"],
        timeout=current_app.config["OPENAI_TIMEOUT_SECONDS"],
        schema=ABDUCTION_AI_REVIEW_OUTPUT_SCHEMA,
        schema_name="save_us_suspected_abduction_review",
        validator=validate_suspected_abduction_review_output,
        fallback_reviewer=deterministic_abduction_ai_review,
        system_instructions="""You are the SAVE-US first-line review assistant for suspected-abduction reports.
Return only the supplied structured JSON schema. Write the public_summary in English.
Never claim to verify facts or contact authorities. Do not include private contact details,
precise street addresses, or internal reasoning in the public_summary.""",
    )


def review_with_openai_or_fallback(
    review_input: Mapping[str, Any],
    *,
    api_key: str | None,
    model: str = "gpt-5.6",
    timeout: float = 20,
    client_factory: Callable[..., Any] | None = None,
    schema: Mapping[str, Any] = AI_REVIEW_OUTPUT_SCHEMA,
    schema_name: str = "save_us_missing_person_review",
    validator: Callable[[Mapping[str, Any]], dict[str, Any]] = validate_ai_review_output,
    fallback_reviewer: Callable[[Mapping[str, Any]], dict[str, Any]] = deterministic_ai_review,
    system_instructions: str = SYSTEM_INSTRUCTIONS,
) -> ReviewExecution:
    """Call Responses API and safely fall back for absent, invalid, or failed live reviews."""
    if not api_key:
        return _fallback(review_input, "OpenAI API key is not configured.", fallback_reviewer)

    try:
        client = _make_client(api_key, timeout, client_factory)
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": json.dumps(review_input, ensure_ascii=False)},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
            store=False,
        )
        raw_output = getattr(response, "output_text", None)
        if not isinstance(raw_output, str) or not raw_output.strip():
            raise ValueError("The OpenAI response did not contain structured output text.")
        parsed_output = json.loads(raw_output)
        return ReviewExecution(
            output=validator(parsed_output),
            source=OPENAI_REVIEW_SOURCE,
        )
    except Exception as error:  # External API, network, parsing, or contract failure.
        return _fallback(review_input, f"Live AI review unavailable: {type(error).__name__}.", fallback_reviewer)


def _make_client(
    api_key: str,
    timeout: float,
    client_factory: Callable[..., Any] | None,
) -> Any:
    """Create an SDK client lazily, preserving a fully offline local test suite."""
    if client_factory is not None:
        return client_factory(api_key=api_key, timeout=timeout)
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("The openai package is not installed.") from error
    return OpenAI(api_key=api_key, timeout=timeout)


def _fallback(
    review_input: Mapping[str, Any],
    reason: str,
    fallback_reviewer: Callable[[Mapping[str, Any]], dict[str, Any]],
) -> ReviewExecution:
    return ReviewExecution(
        output=fallback_reviewer(review_input),
        source=FALLBACK_REVIEW_SOURCE,
        fallback_reason=reason,
    )


__all__ = [
    "OPENAI_REVIEW_SOURCE",
    "ReviewExecution",
    "SYSTEM_INSTRUCTIONS",
    "review_missing_person_alert",
    "review_suspected_abduction_alert",
    "review_with_openai_or_fallback",
]
