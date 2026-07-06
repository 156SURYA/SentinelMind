import socket
import threading
import paramiko
import random
import time
import json
import os

from datetime import datetime

from honeypot.threat_analyzer import analyze_command

from honeypot.behavioral_profiler import (
    profile_attacker
)

from honeypot.predict_next_action import (
    predict_next_action
)

# =========================================
# PERSISTENT HOST KEY
# =========================================

try:
    host_key = paramiko.RSAKey(
        filename="honeypot/server.key"
    )
except:
    host_key = paramiko.RSAKey.generate(2048)
    host_key.write_private_key_file(
        "honeypot/server.key"
    )

# =========================================
# DEPARTMENT MAPPING
# =========================================

DEPARTMENT_MAP = {
    "root":    "Engineering",
    "admin":   "IT",
    "user":    "Finance",
    "ubuntu":  "Operations",
    "guest":   "HR",
}

# =========================================
# APPEND ATTACK LOG (never overwrites)
# =========================================

def append_attack_log(entry: dict, log_path: str = "honeypot/live_attacks.json"):
    """
    Safely appends a new attack entry to live_attacks.json.
    Keeps the last 100 entries. Never overwrites the full file.
    """
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []
    else:
        existing = []

    existing.insert(0, entry)
    existing = existing[:100]

    with open(log_path, "w") as f:
        json.dump(existing, f, indent=2)


# =========================================
# SSH SERVER
# =========================================

class HoneypotServer(paramiko.ServerInterface):

    def __init__(self):
        self.event = threading.Event()
        self.username = "root"

    # =====================================
    # AUTHENTICATION
    # =====================================

    def check_auth_password(self, username, password):
        self.username = username
        print("\n==============================")
        print("🚨 LOGIN ATTEMPT DETECTED")
        print(f"👤 Username: {username}")
        print(f"🔑 Password: {password}")
        return paramiko.AUTH_SUCCESSFUL

    # =====================================
    # CHANNEL REQUEST
    # =====================================

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    # =====================================
    # PTY REQUEST
    # =====================================

    def check_channel_pty_request(
        self, channel, term, width, height,
        pixelwidth, pixelheight, modes
    ):
        return True

    # =====================================
    # SHELL REQUEST
    # =====================================

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True


# =========================================
# CLIENT HANDLER
# =========================================

def handle_client(client, addr):

    print(f"\n🌐 Connection from {addr[0]}")

    transport = paramiko.Transport(client)
    transport.add_server_key(host_key)

    server = HoneypotServer()

    try:
        transport.start_server(server=server)

        channel = transport.accept(20)

        if channel is None:
            print("❌ No channel opened")
            return

        # =================================
        # LOGIN BANNER
        # =================================

        channel.send(
            b"\r\nWelcome to Ubuntu 22.04 LTS\r\n"
        )
        time.sleep(1)

        # =================================
        # SESSION COMMAND TRACKING
        # =================================

        session_commands = []
        session_start = datetime.utcnow()

        # =================================
        # FAKE ATTACKER SESSION
        # =================================

        fake_commands = [
            "whoami",
            "pwd",
            "ls",
            "uname -a",
            "cat /etc/passwd",
            "sudo su",
            "wget malware.sh"
        ]

        for cmd in fake_commands:

            prompt = f"\r\nroot@server:~# {cmd}\r\n"
            channel.send(prompt.encode())

            print("\n🖥️ COMMAND EXECUTED")
            print(f"⚡ {cmd}")

            session_commands.append(cmd)

            # =================================
            # AI THREAT ANALYSIS
            # =================================

            threat = analyze_command(cmd)

            print("\n🧠 AI THREAT ANALYSIS")
            print(f"🚨 Severity: {threat['severity']}")
            print(f"🛡️ Recommended Action: {threat['recommended_action']}")
            print(f"🎯 MITRE ATT&CK: {', '.join(threat['mitre_attack'])}")

            for reason in threat["reasoning"]:
                print(f"📌 {reason}")

            # =================================
            # DETERMINE DEPARTMENT
            # =================================

            username = server.username
            department = DEPARTMENT_MAP.get(username, "Engineering")

            # =================================
            # COMPUTE RISK SCORE
            # =================================

            severity_score = {
                "LOW": 0.2,
                "MEDIUM": 0.5,
                "HIGH": 0.75,
                "CRITICAL": 0.95
            }.get(threat["severity"], 0.5)

            # =================================
            # BUILD UNIFIED ATTACK EVENT
            # (covers both attacker feed
            #  AND insider threat dashboard)
            # =================================

            attack_event = {

                # --- Core attacker fields ---
                "timestamp":            datetime.utcnow().isoformat(),
                "source_ip":            addr[0],
                "username":             username,
                "command":              cmd,
                "severity":             threat["severity"],
                "recommended_action":   threat["recommended_action"],
                "mitre_attack":         threat["mitre_attack"],
                "reasoning":            threat["reasoning"],

                # --- Insider threat / SOC fields ---
                "threat_severity":      threat["severity"],
                "employee_id":          f"EMP-{abs(hash(username)) % 9000 + 1000}",
                "department":           department,
                "files_downloaded":     len(session_commands) * 12,
                "sensitive_docs_accessed": len(session_commands),
                "cloud_upload_mb":      len(session_commands) * 55,
                "geo_distance_km":      random.randint(500, 5000),
                "endpoint_risk_score":  round(severity_score, 2),
                "system_decision":      threat["recommended_action"],

                # --- Session context ---
                "session_commands":     list(session_commands),
                "session_duration_s":   int(
                    (datetime.utcnow() - session_start).total_seconds()
                ),
            }

            # =================================
            # APPEND TO live_attacks.json
            # =================================

            append_attack_log(attack_event)

            print(f"✅ Logged to live_attacks.json")

            # =================================
            # FAKE COMMAND RESPONSES
            # =================================

            if cmd == "whoami":
                response = "root\r\n"

            elif cmd == "pwd":
                response = "/root\r\n"

            elif cmd == "ls":
                response = (
                    "backup.zip\r\n"
                    "employees.db\r\n"
                    "confidential.xlsx\r\n"
                )

            elif cmd == "uname -a":
                response = (
                    "Linux ubuntu-server "
                    "5.15.0-91-generic "
                    "Ubuntu SMP x86_64\r\n"
                )

            elif cmd == "cat /etc/passwd":
                response = (
                    "root:x:0:0:root:/root:/bin/bash\r\n"
                    "ubuntu:x:1000:1000::/home/ubuntu:/bin/bash\r\n"
                )

            elif cmd == "sudo su":
                response = "root access granted\r\n"

            elif cmd == "wget malware.sh":
                response = "Downloading payload...\r\n"

            else:
                fake_responses = [
                    "Permission denied\r\n",
                    "Access restricted\r\n",
                    "Segmentation fault\r\n",
                    "Command executed successfully\r\n"
                ]
                response = random.choice(fake_responses)

            channel.send(response.encode())
            time.sleep(1)

        # =================================
        # AI ATTACKER PROFILING
        # =================================

        profile = profile_attacker(session_commands)

        print("\n🧠 ATTACKER BEHAVIOR PROFILE")
        print(f"🎯 Profile: {profile['attacker_profile']}")
        print(f"📊 Confidence: {profile['confidence']}")

        for reason in profile["reasoning"]:
            print(f"📌 {reason}")

        # =================================
        # STORE PROFILE TELEMETRY
        # =================================

        attack_summary = {
            "timestamp":        datetime.utcnow().isoformat(),
            "source_ip":        addr[0],
            "attacker_profile": profile["attacker_profile"],
            "confidence":       profile["confidence"],
            "session_commands": session_commands,
            "reasoning":        profile["reasoning"]
        }

        try:
            with open("honeypot/attacker_profiles.json", "r") as f:
                profiles = json.load(f)
        except Exception:
            profiles = []

        profiles.insert(0, attack_summary)
        profiles = profiles[:50]

        with open("honeypot/attacker_profiles.json", "w") as f:
            json.dump(profiles, f, indent=2)

        # =================================
        # AI NEXT ACTION PREDICTION
        # =================================

        prediction = predict_next_action(session_commands)

        print("\n🔮 NEXT ACTION PREDICTION")
        print(f"🎯 Predicted Next Action: {prediction['predicted_next_action']}")
        print(f"📊 Prediction Confidence: {prediction['confidence']}")

        for reason in prediction["reasoning"]:
            print(f"📌 {reason}")

        # =================================
        # STORE PREDICTIVE TELEMETRY
        # =================================

        predictive_event = {
            "timestamp":             datetime.utcnow().isoformat(),
            "source_ip":             addr[0],
            "attacker_profile":      profile["attacker_profile"],
            "predicted_next_action": prediction["predicted_next_action"],
            "prediction_confidence": prediction["confidence"],
            "session_commands":      session_commands,
            "reasoning":             prediction["reasoning"]
        }

        try:
            with open("honeypot/predictions.json", "r") as f:
                predictions = json.load(f)
        except Exception:
            predictions = []

        predictions.insert(0, predictive_event)
        predictions = predictions[:50]

        with open("honeypot/predictions.json", "w") as f:
            json.dump(predictions, f, indent=2)

        # =================================
        # SESSION CLOSE
        # =================================

        channel.send(b"\r\nSession closed.\r\n")
        time.sleep(1)
        channel.close()

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        transport.close()


# =========================================
# START HONEYPOT
# =========================================

def start_honeypot():

    server_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server_socket.bind(("0.0.0.0", 2222))
    server_socket.listen(100)

    print("\n🛡️ SSH Honeypot Running on Port 2222...")

    while True:
        client, addr = server_socket.accept()

        client_thread = threading.Thread(
            target=handle_client,
            args=(client, addr)
        )

        client_thread.daemon = True
        client_thread.start()


# =========================================
# MAIN
# =========================================

if __name__ == "__main__":
    start_honeypot()