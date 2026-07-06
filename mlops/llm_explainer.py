# mlops/llm_explainer.py
import anthropic
import json

client = anthropic.Anthropic()


def generate_soc_brief(
    session_commands: list[str],
    prediction: dict,
    shap_values: list[tuple],
    attacker_profile: dict
) -> dict:
    """
    Uses Claude to generate a human-readable SOC analyst brief
    from raw model outputs.
    """

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


def generate_counterfactual(
    session_commands: list[str],
    current_severity: str
) -> str:
    """
    Explains what the attacker would have needed to do differently
    to avoid detection — useful for tuning deception strategies.
    """

    prompt = f"""
A honeypot session was classified as {current_severity}.

Commands observed: {json.dumps(session_commands)}

In 2 sentences: what specific behavioral changes would have made this 
session appear less suspicious to an ML anomaly detector? 
Focus on timing, command ordering, and obfuscation patterns.
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text