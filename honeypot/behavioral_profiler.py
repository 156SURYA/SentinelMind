def profile_attacker(commands):

    commands = [
        cmd.lower()
        for cmd in commands
    ]

    profile = "Unknown"

    confidence = 0.50

    reasoning = []

    # =====================================
    # RECON SCANNER
    # =====================================

    recon_keywords = [

        "whoami",

        "pwd",

        "ls",

        "uname",

        "ifconfig"
    ]

    recon_count = sum(

        any(keyword in cmd for keyword in recon_keywords)

        for cmd in commands
    )

    # =====================================
    # CREDENTIAL HUNTER
    # =====================================

    credential_keywords = [

        "/etc/passwd",

        "/etc/shadow",

        "ssh"
    ]

    credential_count = sum(

        any(keyword in cmd for keyword in credential_keywords)

        for cmd in commands
    )

    # =====================================
    # PRIVILEGE ESCALATION
    # =====================================

    privilege_keywords = [

        "sudo",

        "su "
    ]

    privilege_count = sum(

        any(keyword in cmd for keyword in privilege_keywords)

        for cmd in commands
    )

    # =====================================
    # MALWARE OPERATOR
    # =====================================

    malware_keywords = [

        "wget",

        "curl",

        "powershell",

        "nc",

        "netcat"
    ]

    malware_count = sum(

        any(keyword in cmd for keyword in malware_keywords)

        for cmd in commands
    )

    # =====================================
    # CLASSIFICATION LOGIC
    # =====================================

    if malware_count >= 1:

        profile = "Malware Operator"

        confidence = 0.95

        reasoning.append(
            "Malware delivery behavior observed"
        )

    elif privilege_count >= 1:

        profile = "Privilege Escalation Operator"

        confidence = 0.90

        reasoning.append(
            "Privilege escalation attempts detected"
        )

    elif credential_count >= 1:

        profile = "Credential Hunter"

        confidence = 0.85

        reasoning.append(
            "Credential access patterns observed"
        )

    elif recon_count >= 3:

        profile = "Reconnaissance Scanner"

        confidence = 0.80

        reasoning.append(
            "Reconnaissance-heavy session detected"
        )

    # =====================================
    # HUMAN VS AUTOMATED
    # =====================================

    if len(commands) > 5:

        reasoning.append(
            "Extended interactive session observed"
        )

    return {

        "attacker_profile":
            profile,

        "confidence":
            round(confidence, 2),

        "reasoning":
            reasoning
    }