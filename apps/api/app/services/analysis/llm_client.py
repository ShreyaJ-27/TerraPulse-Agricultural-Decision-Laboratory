from __future__ import annotations

import logging
import os
from typing import Literal

import httpx
from app.services.analysis.models import (
    AnalysisSection,
    EvidenceBundle,
    GroundedClaim,
)
from app.services.analysis.validator import QuantitativeClaimValidator

logger = logging.getLogger("terrapulse.analysis.llm_client")


class AnalysisLlmClient:
    """Optional client for invoking Gemini models to generate grounded explanations,

    with strict timeouts, network isolation handling, and zero-hallucination post-validation.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-2.5-flash",
        timeout_seconds: float = 5.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def generate_explanation(
        self,
        bundle: EvidenceBundle,
        question: str | None,
        language: Literal["en", "kn", "hi"] = "en",
    ) -> tuple[str, list[AnalysisSection], list[GroundedClaim]] | None:
        """Attempts LLM explanation generation.

        Returns None if not configured, timed out, network error, or if post-validation detects
        ungrounded/hallucinated numbers.
        """
        if not self.is_configured:
            logger.debug("Gemini API key not configured; proceeding with deterministic engine.")
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        system_instruction = (
            "You are an agricultural biophysical analyst for TerraPulse. "
            "You MUST ONLY use facts and numbers present in the provided JSON evidence bundle. "
            "NEVER invent, hallucinate, extrapolate, or estimate numerical measurements, yields, or weather values. "
            "NEVER diagnose plant diseases or pests; refuse them and refer to Krishi Vigyan Kendra (KVK). "
            "NEVER predict commodity or mandi market prices; refuse them as out of biophysical scope. "
            f"Respond in language code '{language}'."
        )

        bundle_dict = bundle.model_dump(mode="json", by_alias=True)
        user_prompt = (
            f"User Question: {question or 'Provide an agro-ecological assessment of the plot.'}\n\n"
            f"Authoritative Evidence Bundle:\n{bundle_dict}\n\n"
            "Generate an evidence-grounded summary adhering strictly to the above facts."
        )

        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 1000,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(url, headers=headers, params=params, json=payload)
                if resp.status_code != 200:
                    logger.warning("Gemini API returned status %d: %s", resp.status_code, resp.text)
                    return None

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return None

                candidate_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if not candidate_text:
                    return None

                # Strict validation of generated text against authoritative evidence numbers
                is_grounded, ungrounded_numbers = QuantitativeClaimValidator.validate_text(
                    candidate_text, bundle, []
                )

                if not is_grounded:
                    logger.warning(
                        "LLM candidate explanation rejected due to ungrounded numbers: %s",
                        ungrounded_numbers,
                    )
                    return None

                # Assemble single-section structured explanation
                section = AnalysisSection(
                    key="llm_explanation",
                    title="Grounded Agro-Ecological Analysis",
                    content=candidate_text,
                    claims=[],
                )
                return candidate_text, [section], []

        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.info("LLM request failed or timed out (%s); falling back to deterministic explainer.", exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected error during LLM invocation: %s", exc)
            return None
