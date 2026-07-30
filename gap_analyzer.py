"""
Takes a (new_circular_clause, matched_old_policy_clause) pair and decides:
compliant / gap / conflict / no_existing_policy.

- MockLLM: rule-of-thumb heuristic, zero API cost, used in LOCAL_TEST_MODE
  so you can demo the full pipeline without an API key.
- ClaudeGapAnalyzer: real call to Claude for the actual hackathon demo.
"""

import json
import re
from config import LOCAL_TEST_MODE, ANTHROPIC_API_KEY, ANTHROPIC_MODEL


PROMPT_TEMPLATE = """You are a compliance analyst. Compare the new regulatory \
clause against the company's existing policy clause and decide if the \
existing policy still complies.

New regulatory clause:
\"\"\"{new_clause}\"\"\"

Closest existing company policy clause found:
\"\"\"{old_clause}\"\"\"

Respond with ONLY a JSON object, no other text, in this exact shape:
{{"status": "compliant" | "gap" | "conflict" | "no_existing_policy",
  "explanation": "one sentence explaining the verdict",
  "suggested_edit": "one sentence suggested policy fix, or null if compliant"}}
"""


class MockLLM:
    """
    Heuristic stand-in for an LLM call. Uses word-overlap similarity as a
    crude proxy for "does the old clause already cover this new clause".
    Good enough to validate the pipeline end-to-end offline; NOT a
    substitute for the real model in the actual demo.
    """

    def analyze(self, new_clause: str, old_clause: str, match_score: float) -> dict:
        new_words = set(re.findall(r"\w+", new_clause.lower()))
        old_words = set(re.findall(r"\w+", old_clause.lower()))
        overlap = len(new_words & old_words) / max(len(new_words), 1)

        if match_score < 0.08:
            return {
                "status": "no_existing_policy",
                "explanation": "No sufficiently similar clause found in the existing policy.",
                "suggested_edit": "Add a new clause covering this requirement.",
            }
        if overlap > 0.45:
            return {
                "status": "compliant",
                "explanation": "Existing clause substantially overlaps with the new requirement.",
                "suggested_edit": None,
            }
        if overlap > 0.2:
            return {
                "status": "gap",
                "explanation": "Existing clause is related but does not fully cover the new requirement.",
                "suggested_edit": "Update the existing clause to explicitly include the new requirement's terms.",
            }
        return {
            "status": "conflict",
            "explanation": "Existing clause appears to address the same topic but may contradict the new requirement.",
            "suggested_edit": "Review and align the existing clause with the new circular's wording.",
        }


class ClaudeGapAnalyzer:
    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def analyze(self, new_clause: str, old_clause: str, match_score: float) -> dict:
        prompt = PROMPT_TEMPLATE.format(new_clause=new_clause, old_clause=old_clause)
        response = self.client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text.strip()
        raw_text = re.sub(r"^```json|```$", "", raw_text).strip()
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "explanation": f"Could not parse LLM response: {raw_text[:200]}",
                "suggested_edit": None,
            }


def get_gap_analyzer():
    if LOCAL_TEST_MODE:
        return MockLLM()
    return ClaudeGapAnalyzer()
