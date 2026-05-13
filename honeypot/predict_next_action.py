def predict_next_action(commands):

    commands = [
        cmd.lower()
        for cmd in commands
    ]

    prediction = "Unknown"

    confidence = 0.50

    reasoning = []

    # =====================================
    # RECON → CREDENTIAL ACCESS
    # =====================================

    recon_commands = [

        "whoami",

        "pwd",

        "ls",

        "uname"
    ]

    recon_detected = any(

        any(keyword in cmd for keyword in recon_commands)

        for cmd in commands
    )

    credential_detected = any(

        "/etc/passwd" in cmd
        or "/etc/shadow" in cmd

        for cmd in commands
    )

    privilege_detected = any(

        "sudo" in cmd
        or "su " in cmd

        for cmd in commands
    )

    malware_detected = any(

        "wget" in cmd
        or "curl" in cmd
        or "nc" in cmd

        for cmd in commands
    )

    # =====================================
    # PREDICTION ENGINE
    # =====================================

    if recon_detected and not credential_detected:

        prediction = (
            "Credential Enumeration Attempt"
        )

        confidence = 0.80

        reasoning.append(
            "Reconnaissance behavior typically "
            "precedes credential access attempts"
        )

    elif credential_detected and not privilege_detected:

        prediction = (
            "Privilege Escalation Attempt"
        )

        confidence = 0.87

        reasoning.append(
            "Credential access often precedes "
            "privilege escalation"
        )

    elif privilege_detected and not malware_detected:

        prediction = (
            "Malware Deployment"
        )

        confidence = 0.93

        reasoning.append(
            "Privilege escalation commonly "
            "precedes payload deployment"
        )

    elif malware_detected:

        prediction = (
            "Persistence or Lateral Movement"
        )

        confidence = 0.96

        reasoning.append(
            "Malware deployment suggests "
            "post-exploitation activity"
        )

    return {

        "predicted_next_action":
            prediction,

        "confidence":
            round(confidence, 2),

        "reasoning":
            reasoning
    }