import copy
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


CLIENT_ID = os.environ["BAZA_HAPP_TEST_UUID"]
CONFIG_PATH = Path("/usr/local/etc/xray/config.json")
TEST_TAG = "vless-reality-happ-test-443"


def main() -> None:
    original = CONFIG_PATH.read_text()
    data = json.loads(original)
    inbounds = data.setdefault("inbounds", [])
    source = next(
        inbound
        for inbound in inbounds
        if inbound.get("protocol") == "vless" and inbound.get("port") == 8443
    )
    test = next((inbound for inbound in inbounds if inbound.get("tag") == TEST_TAG), None)

    if test is None:
        test = copy.deepcopy(source)
        test["tag"] = TEST_TAG
        test["port"] = 443
        test.setdefault("settings", {})["clients"] = []
        inbounds.append(test)
    else:
        test["port"] = 443
        test["protocol"] = "vless"
        test["streamSettings"] = copy.deepcopy(source.get("streamSettings", {}))
        test.setdefault("settings", {})["decryption"] = source.get("settings", {}).get(
            "decryption",
            "none",
        )

    clients = test.setdefault("settings", {}).setdefault("clients", [])
    exists = any(client.get("id") == CLIENT_ID for client in clients)
    if not exists:
        clients.append({"id": CLIENT_ID, "email": "baza-user-1-happ-no-flow"})
    for client in clients:
        client.pop("flow", None)

    new_text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    changed = original != new_text
    if changed:
        backup = CONFIG_PATH.with_name(
            f"config.json.backup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        )
        backup.write_text(original)
        os.chmod(backup, 0o640)

        tmp = CONFIG_PATH.with_suffix(".json.tmp")
        tmp.write_text(new_text)
        os.chmod(tmp, 0o640)
        tmp.replace(CONFIG_PATH)

    subprocess.check_call(["xray", "run", "-test", "-config", str(CONFIG_PATH)])
    subprocess.check_call(["chown", "nobody:nogroup", str(CONFIG_PATH)])
    subprocess.check_call(["chmod", "640", str(CONFIG_PATH)])
    if changed:
        subprocess.check_call(["systemctl", "restart", "xray"])

    print("changed=", changed)
    print("client_exists_before=", exists)
    print("credential_sha256_12=", hashlib.sha256(CLIENT_ID.encode()).hexdigest()[:12])
    print("inbounds=", [(inbound.get("tag"), inbound.get("port")) for inbound in inbounds])


if __name__ == "__main__":
    main()
