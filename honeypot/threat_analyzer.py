# =========================================
# honeypot/threat_analyzer.py
# =========================================

import numpy as np

from mlops.drift_monitor import check_drift

# =========================================
# DRIFT TRACKING
# =========================================

SESSION_COUNT = 0

EMBEDDING_BUFFER = []

# =========================================
# DRIFT-AWARE ANALYSIS
# =========================================

def analyze_with_drift_check(
    session_embedding: np.ndarray,
    analyzer
):

    """
    Performs threat analysis and periodically
    checks for behavioral drift.
    """

    global SESSION_COUNT
    global EMBEDDING_BUFFER

    EMBEDDING_BUFFER.append(
        session_embedding
    )

    SESSION_COUNT += 1

    # =====================================
    # RUN DRIFT CHECK EVERY 100 SESSIONS
    # =====================================

    if SESSION_COUNT % 100 == 0:

        current_batch = np.array(
            EMBEDDING_BUFFER[-100:]
        )

        try:

            drift_status = check_drift(
                current_batch
            )

            if drift_status.get(
                "drift_detected",
                False
            ):

                print(
                    "[ThreatAnalyzer] "
                    "Behavioral drift detected — "
                    "consider retraining."
                )

        except Exception as e:

            print(
                f"[ThreatAnalyzer] "
                f"Drift check failed: {e}"
            )

    # =====================================
    # RETURN ANALYZER RESULT
    # =====================================

    return analyzer.analyze(
        session_embedding
    )

# =========================================
# COMMAND ANALYSIS ENGINE
# =========================================

def analyze_command(command):

    """
    Rule-based threat analysis for
    honeypot command inspection.
    """

    command = command.lower()

    # =====================================
    # DEFAULT VALUES
    # =====================================

    severity = "LOW"

    action = "ALLOW"

    reasoning = []

    mitre = []

    # =====================================
    # RECONNAISSANCE COMMANDS
    # =====================================

    recon_commands = [

        "whoami",

        "pwd",

        "ls",

        "uname",

        "ifconfig",

        "ipconfig",

        "hostname",

        "netstat"
    ]

    for cmd in recon_commands:

        if cmd in command:

            severity = "LOW"

            action = "MONITOR"

            reasoning.append(
                "System reconnaissance "
                "behavior detected"
            )

            mitre.append(
                "Discovery"
            )

    # =====================================
    # CREDENTIAL ACCESS
    # =====================================

    credential_keywords = [

        "/etc/passwd",

        "/etc/shadow",

        "sam",

        "mimikatz"
    ]

    for keyword in credential_keywords:

        if keyword in command:

            severity = "MEDIUM"

            action = "CHALLENGE_MFA"

            reasoning.append(
                "Credential enumeration "
                "attempt detected"
            )

            mitre.append(
                "Credential Access"
            )

    # =====================================
    # PRIVILEGE ESCALATION
    # =====================================

    privilege_keywords = [

        "sudo",

        "su ",

        "chmod 777",

        "setuid"
    ]

    for keyword in privilege_keywords:

        if keyword in command:

            severity = "HIGH"

            action = "ISOLATE_ENDPOINT"

            reasoning.append(
                "Privilege escalation "
                "activity detected"
            )

            mitre.append(
                "Privilege Escalation"
            )

    # =====================================
    # MALWARE / PAYLOAD DELIVERY
    # =====================================

    malware_keywords = [

        "wget",

        "curl",

        ".sh",

        "powershell",

        "nc",

        "netcat",

        "bash -i",

        "python -c",

        "perl -e"
    ]

    for keyword in malware_keywords:

        if keyword in command:

            severity = "CRITICAL"

            action = "BLOCK_AND_ALERT"

            reasoning.append(
                "Possible malware delivery "
                "activity detected"
            )

            mitre.append(
                "Command and Control"
            )

    # =====================================
    # DATA EXFILTRATION
    # =====================================

    exfiltration_keywords = [

        "scp",

        "ftp",

        "sftp",

        "rsync"
    ]

    for keyword in exfiltration_keywords:

        if keyword in command:

            severity = "HIGH"

            action = "BLOCK_AND_ALERT"

            reasoning.append(
                "Potential data exfiltration "
                "activity detected"
            )

            mitre.append(
                "Exfiltration"
            )

    # =====================================
    # REMOVE DUPLICATES
    # =====================================

    reasoning = list(
        set(reasoning)
    )

    mitre = list(
        set(mitre)
    )

    # =====================================
    # SAFE COMMAND HANDLING
    # =====================================

    if len(reasoning) == 0:

        reasoning.append(
            "Behavior appears normal"
        )

    # =====================================
    # FINAL RESULT
    # =====================================

    return {

        "command":
            command,

        "severity":
            severity,

        "recommended_action":
            action,

        "reasoning":
            reasoning,

        "mitre_attack":
            mitre
    }