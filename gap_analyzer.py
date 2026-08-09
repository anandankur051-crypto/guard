"""
Gap analysis for RegTrack.

- MockLLM: rule-based offline analyzer.
- GeminiGapAnalyzer: Gemini-based compliance analysis.
"""

import json
import re

from config import (
    LOCAL_TEST_MODE,
    GEMINI_API_KEY,
    GEMINI_MODEL,
)


PROMPT_TEMPLATE = """
You are a regulatory compliance analyst.

Compare the NEW regulatory requirement with the EXISTING company policy.

NEW REGULATORY REQUIREMENT:
{new_clause}

EXISTING COMPANY POLICY:
{old_clause}

Classify the existing policy as exactly one of:

- compliant: the existing policy adequately covers the new requirement
- gap: the existing policy is related but needs additional requirements
- conflict: the existing policy contradicts the new requirement
- no_existing_policy: the policy does not meaningfully address the requirement

Important:
- Do not treat generic words like "compliance", "regulatory", or "company"
  as evidence of a meaningful match.
- Focus on the actual regulatory subject and obligation.
- Keep the explanation to ONE short sentence.
- Keep the suggested_edit to ONE short sentence.
- If status is compliant, suggested_edit must be null.

Return ONLY JSON.
"""


class MockLLM:
    """
    Rule-based stand-in used in LOCAL_TEST_MODE.
    """

    def analyze(
        self,
        new_clause: str,
        old_clause: str,
        match_score: float
    ) -> dict:

        new_words = set(
            re.findall(r"\w+", new_clause.lower())
        )

        old_words = set(
            re.findall(r"\w+", old_clause.lower())
        )

        overlap = (
            len(new_words & old_words)
            / max(len(new_words), 1)
        )

        if match_score < 0.08:
            return {
                "status": "no_existing_policy",
                "explanation": (
                    "No sufficiently similar policy clause was found."
                ),
                "suggested_edit": (
                    "Add a new policy clause covering this requirement."
                ),
            }

        if overlap > 0.45:
            return {
                "status": "compliant",
                "explanation": (
                    "The existing policy substantially covers the requirement."
                ),
                "suggested_edit": None,
            }

        if overlap > 0.20:
            return {
                "status": "gap",
                "explanation": (
                    "The existing policy addresses the topic but lacks "
                    "some required details."
                ),
                "suggested_edit": (
                    "Update the policy to explicitly include the new requirement."
                ),
            }

        return {
            "status": "conflict",
            "explanation": (
                "The existing policy may contradict the new requirement."
            ),
            "suggested_edit": (
                "Review and align the policy with the new regulatory requirement."
            ),
        }


class GeminiGapAnalyzer:

    def __init__(self):

        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is required when "
                "REGTRACK_LOCAL_TEST_MODE=false"
            )

        from google import genai

        self.client = genai.Client(
            api_key=GEMINI_API_KEY
        )

    def analyze(
        self,
        new_clause: str,
        old_clause: str,
        match_score: float
    ) -> dict:

        prompt = PROMPT_TEMPLATE.format(
            new_clause=new_clause,
            old_clause=old_clause,
        )

        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",

                "response_json_schema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": [
                                "compliant",
                                "gap",
                                "conflict",
                                "no_existing_policy",
                            ],
                        },
                        "explanation": {
                            "type": "string",
                        },
                        "suggested_edit": {
                            "type": [
                                "string",
                                "null",
                            ],
                        },
                    },
                    "required": [
                        "status",
                        "explanation",
                        "suggested_edit",
                    ],
                },

                "max_output_tokens": 500,
            },
        )

        raw_text = response.text.strip()

        try:

            result = json.loads(raw_text)

            return {
                "status": result.get("status"),
                "explanation": result.get("explanation"),
                "suggested_edit": result.get("suggested_edit"),
            }

        except (json.JSONDecodeError, TypeError):

            return {
                "status": "error",
                "explanation": (
                    f"Could not parse LLM response: "
                    f"{raw_text[:300]}"
                ),
                "suggested_edit": None,
            }


def get_gap_analyzer():

    if LOCAL_TEST_MODE:
        return MockLLM()

    return GeminiGapAnalyzer()