def analyze_command(command):

    command = command.lower()

    # =====================================
    # DEFAULT
    # =====================================

    severity = "LOW"

    action = "ALLOW"

    reasoning = []

    mitre = []

    # =====================================
    # RECON COMMANDS
    # =====================================

    recon_commands = [

        "whoami",

        "pwd",

        "ls",

        "uname",

        "ifconfig",

        "ipconfig"
    ]

    for cmd in recon_commands:

        if cmd in command:

            severity = "LOW"

            action = "MONITOR"

            reasoning.append(
                "System reconnaissance behavior detected"
            )

            mitre.append(
                "Discovery"
            )

    # =====================================
    # CREDENTIAL ACCESS
    # =====================================

    if "/etc/passwd" in command:

        severity = "MEDIUM"

        action = "CHALLENGE_MFA"

        reasoning.append(
            "Credential enumeration attempt detected"
        )

        mitre.append(
            "Credential Access"
        )

    # =====================================
    # PRIVILEGE ESCALATION
    # =====================================

    if "sudo" in command:

        severity = "HIGH"

        action = "ISOLATE_ENDPOINT"

        reasoning.append(
            "Privilege escalation activity detected"
        )

        mitre.append(
            "Privilege Escalation"
        )

    # =====================================
    # MALWARE DOWNLOAD
    # =====================================

    malware_keywords = [

        "wget",

        "curl",

        ".sh",

        "powershell",

        "nc",

        "netcat"
    ]

    for keyword in malware_keywords:

        if keyword in command:

            severity = "CRITICAL"

            action = "BLOCK_AND_ALERT"

            reasoning.append(
                "Possible malware delivery activity detected"
            )

            mitre.append(
                "Command and Control"
            )

    # =====================================
    # FINAL RESULT
    # =====================================

    return {

        "command": command,

        "severity": severity,

        "recommended_action": action,

        "reasoning": reasoning,

        "mitre_attack": mitre
    }