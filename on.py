import requests
import json
import time
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = "auth_token.json"
RESPONSE_FILE = "response_data.json"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")


def authenticate(url, username, password, account_name):
    headers = {"Content-Type": "application/json"}
    payload = {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "name": username,
                        "password": password,
                        "domain": {"name": account_name}
                    }
                }
            },
            "scope": {
                "project": {
                    "domain": {"name": account_name},
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
            log("Authentication successful.")
            return token
        else:
            log(f"Authentication failed: {response.status_code}")
            log(response.text)
    except requests.exceptions.RequestException as e:
        log(f"Auth error: {e}")
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
            log(f"VM {vm_id} action '{action['action']}' successful.")
            return True
        else:
            log(f"VM {vm_id} action failed. Status: {response.status_code}")
            log(response.text)
            return False
    except requests.exceptions.RequestException as e:
        log(f"VM {vm_id} action error: {e}")
        return False


def process_batches(endpoint, token, batches, action):
    for batch_index, batch in enumerate(batches, start=1):
        log(f"\nStarting batch {batch_index} with VMs: {batch}")
        attempts = 0
        success = False

        while attempts < MAX_RETRIES and not success:
            success = True  # Assume success unless one VM fails
            for vm_id in batch:
                vm_success = vm_action(endpoint, vm_id, token, action)
                if not vm_success:
                    success = False
                    log(f"Retry attempt {attempts + 1} failed for VM: {vm_id}")
            if not success:
                attempts += 1
                if attempts < MAX_RETRIES:
                    log(f"Retrying batch {batch_index} after {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    log(f"Batch {batch_index} failed after {MAX_RETRIES} attempts.")
            else:
                log(f"Batch {batch_index} completed successfully.")
                break


if __name__ == "__main__":
    ENDPOINT = os.getenv("AUTH_ENDPOINT")
    USERNAME = os.getenv("AUTH_USERNAME")
    PASSWORD = os.getenv("AUTH_PASSWORD")
    ACCOUNT_NAME = os.getenv("AUTH_ACCOUNT_NAME")
    AUTH_URL = f"https://{ENDPOINT}/api/v2/identity/auth"
    ON_ACTION = {"action": "powerup"}
    OFF_ACTION = {"action": "shutdown", "force": False}

    # Define your VM batches here (list of list)
    VM_BATCHES = [
        ["5435bf96-3911-4ae5-adf1-97d47fb890cf"]
    ]

    token = authenticate(AUTH_URL, USERNAME, PASSWORD, ACCOUNT_NAME)
    if token:
        process_batches(ENDPOINT, token, VM_BATCHES, ON_ACTION)
    else:
        log("Authentication failed. Skipping batch processing.")
