def decide_action(threat_level: str) -> str:
    """
    Converts threat level into an enforcement action
    """

    if threat_level == "LOW":
        return "ALLOW"

    if threat_level == "MEDIUM":
        return "CHALLENGE"   # CAPTCHA / MFA

    return "BLOCK"
