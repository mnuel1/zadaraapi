import requests
import json
import time
import os
from datetime import datetime

TOKEN_FILE = "auth_token.json"
RESPONSE_FILE = "response_data.json"


def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")


def authenticate(url, username, password, account_name):
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "name": username,
                        "password": password,
                        "domain": {
                            "name": account_name
                        }
                    }
                }
            },
            "scope": {
                "project": {
                    "domain": {
                    "name": account_name
                    },
                    "name": "default"
                }
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), verify=False)
        if response.status_code == 201:
            token = response.headers.get("X-Subject-Token")
            with open(TOKEN_FILE, "w") as f:
                json.dump({"token": token, "timestamp": int(time.time())}, f)
            log("Authentication successful. Token saved.")
            return token
        else:
            log(f"Authentication failed. Status code: {response.status_code}")
            log(response.text)
            return None
    except requests.exceptions.RequestException as e:
        log(f"Auth error: {e}")
        return None


def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            return token_data.get("token")
    return None


def vm_action(endpoint, vm_id, token, action):
    url = f"https://{endpoint}/api/v2/compute/vms/{vm_id}/action"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-Auth-Token": token
    }

    try:
        response = requests.post(url, headers=headers, json=action, verify=False)
        if response.status_code == 200:
            data = response.json()
            with open(RESPONSE_FILE, "w") as json_file:
                json.dump(data, json_file, indent=4)
            log(f"VM action '{action['action']}' successful.")
        else:
            log(f"VM action failed. Status code: {response.status_code}")
            log(response.text)
    except requests.exceptions.RequestException as e:
        log(f"VM action error: {e}")


def get_vms(url, token):
    headers = {
        "accept": "application/json",
        "X-Auth-Token": token
    }

    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            data = response.json()
            with open(RESPONSE_FILE, "w") as json_file:
                json.dump(data, json_file, indent=4)
            log("VMs fetched successfully.")
        else:
            log(f"Failed to retrieve VMs. Status code: {response.status_code}")
            log(response.text)
    except requests.exceptions.RequestException as e:
        log(f"Get VMs error: {e}")


if __name__ == "__main__":
    # Configuration (fill in or use environment variables for security)
    ENDPOINT = "27.126.152.210"
    AUTH_URL = f"https://{ENDPOINT}/api/v2/identity/auth"
    USERNAME = "sandzsupport"
    PASSWORD = "Peas+ahQyg1"
    ACCOUNT_NAME = "cloud_msp"

    VM_ID = ["5435bf96-3911-4ae5-adf1-97d47fb890cf"]

    # Choose action (manually set or pass via CLI args or env vars)
    ACTION = {"action": "powerup"}
    # ACTION = {"action": "shutdown", "force": False}

    # Step 1: Authenticate and save token every 4 hours (run via cron)
    token = authenticate(AUTH_URL, USERNAME, PASSWORD, ACCOUNT_NAME)

    if token:
        vm_action(ENDPOINT, VM_ID, token, ACTION)
        # Optional: get VMs
        # get_vms("https://27.126.152.210/api/v2/compute/vms", token)
    else:
        log("Token not available. Skipping VM action.")
