# mlops/llm_explainer.py
import anthropic
import json
import os

# =========================================
# MOCK MODE
# If no API key is configured, fall back to
# templated responses instead of failing —
# lets the rest of the platform run/demo
# without requiring a funded Anthropic key.
# =========================================

MOCK_MODE = not os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic() if not MOCK_MODE else None


def generate_soc_brief(
    session_commands: list[str],
    prediction: dict,
    shap_values: list[tuple],
    attacker_profile: dict
) -> dict:
    """
    Uses Claude to generate a human-readable SOC analyst brief
    from raw model outputs. Falls back to a templated brief
    if ANTHROPIC_API_KEY isn't configured.
    """

    if MOCK_MODE:
        severity = prediction.get("severity", "UNKNOWN")
        confidence = prediction.get("confidence", 0.0)
        profile = attacker_profile.get("profile", "Unknown")
        indicators = ", ".join(attacker_profile.get("indicators", [])) or "none listed"

        mock_brief = (
            "[MOCK MODE — no ANTHROPIC_API_KEY configured, showing templated output]\n\n"
            f"1. THREAT SUMMARY: Session flagged {severity} severity "
            f"with {confidence:.0%} model confidence across {len(session_commands)} observed commands.\n"
            f"2. LIKELY INTENT: Behavior consistent with a '{profile}' profile "
            f"(indicators: {indicators}).\n"
            f"3. RECOMMENDED ACTION: Escalate per {severity} severity threshold; review session log.\n"
            f"4. CONFIDENCE ASSESSMENT: Prediction set = {prediction.get('prediction_set', [])} "
            f"(conformal coverage, not a point estimate)."
        )

        return {
            "soc_brief": mock_brief,
            "model": "mock (no ANTHROPIC_API_KEY set)",
            "input_severity": prediction.get("severity"),
            "input_confidence": prediction.get("confidence")
        }

    shap_summary = "\n".join([
        f"  - Feature '{feat}': contribution {val:+.3f}"
        for feat, val in shap_values[:5]
    ])

    prompt = f"""
You are a senior SOC analyst assistant. A machine learning system has flagged 
an active honeypot session. Generate a concise analyst brief.

SESSION COMMANDS OBSERVED:
{json.dumps(session_commands, indent=2)}

ML MODEL OUTPUT:
- Severity: {prediction.get('severity', 'UNKNOWN')}
- Confidence: {prediction.get('confidence', 0.0):.2f}
- Prediction set (conformal): {prediction.get('prediction_set', [])}

ATTACKER PROFILE:
- Type: {attacker_profile.get('profile', 'Unknown')}
- Behavioral indicators: {attacker_profile.get('indicators', [])}

TOP SHAP FEATURE CONTRIBUTIONS:
{shap_summary}

Provide:
1. THREAT SUMMARY (2 sentences max)
2. LIKELY INTENT (1 sentence)
3. RECOMMENDED ACTION (specific, actionable)
4. CONFIDENCE ASSESSMENT (1 sentence on model certainty)

Be direct. No preamble.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        raw_text = response.content[0].text

        return {
            "soc_brief": raw_text,
            "model": "claude-sonnet-4-20250514",
            "input_severity": prediction.get("severity"),
            "input_confidence": prediction.get("confidence")
        }
    except Exception as e:
        return {
            "soc_brief": f"[LLM call failed: {e}]",
            "model": "claude-sonnet-4-20250514 (call failed)",
            "input_severity": prediction.get("severity"),
            "input_confidence": prediction.get("confidence")
        }


def generate_counterfactual(
    session_commands: list[str],
    current_severity: str
) -> str:
    """
    Explains what the attacker would have needed to do differently
    to avoid detection. Falls back to a templated response if
    ANTHROPIC_API_KEY isn't configured.
    """

    if MOCK_MODE:
        return (
            "[MOCK MODE — no ANTHROPIC_API_KEY configured] "
            f"A session classified as {current_severity} would typically evade detection "
            "by spacing commands over a longer interval, avoiding known high-signal "
            "commands, and blending in with baseline traffic patterns."
        )

    prompt = f"""
A honeypot session was classified as {current_severity}.

Commands observed: {json.dumps(session_commands)}

In 2 sentences: what specific behavioral changes would have made this 
session appear less suspicious to an ML anomaly detector? 
Focus on timing, command ordering, and obfuscation patterns.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"[LLM call failed: {e}]"