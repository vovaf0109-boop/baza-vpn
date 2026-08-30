"""Apply the A-D VLESS/REALITY test matrix to a lab Xray node.

flow is a per-client setting, so both variants of a port share one inbound:
  443  -> A no-flow, B vision
  8443 -> C no-flow, D vision
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CONFIG_PATH = Path("/usr/local/etc/xray/config.json")
INBOUND_443_TAG = "vless-reality-matrix-443"
VISION_FLOW = "xtls-rprx-vision"


def _required_uuid(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing {name}")
    return value


def _sha12(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def _ensure_inbound(inbounds: list[dict], *, port: int, tag: str, source: dict) -> dict:
    existing = next(
        (
            inbound
            for inbound in inbounds
            if inbound.get("port") == port and inbound.get("protocol") == "vless"
        ),
        None,
    )
    if existing is None:
        inbound = copy.deepcopy(source)
        inbound["tag"] = tag
        inbound["port"] = port
        inbound.setdefault("settings", {})["clients"] = []
        inbounds.append(inbound)
        return inbound

    existing["port"] = port
    existing["protocol"] = "vless"
    if port != source.get("port"):
        existing["tag"] = existing.get("tag") or tag
        existing["streamSettings"] = copy.deepcopy(source.get("streamSettings", {}))
        existing.setdefault("settings", {})["decryption"] = source.get("settings", {}).get(
            "decryption",
            "none",
        )
    return existing


def _upsert_client(clients: list[dict], *, client_id: str, email: str, flow: str | None) -> None:
    client = next((item for item in clients if item.get("id") == client_id), None)
    if client is None:
        client = {"id": client_id, "email": email}
        clients.append(client)
    client["email"] = email
    if flow:
        client["flow"] = flow
    else:
        client.pop("flow", None)


def main() -> None:
    matrix = {
        "A": {"uuid": _required_uuid("BAZA_MATRIX_A_UUID"), "port": 443, "flow": None, "email": "matrix-a-443-no-flow"},
        "B": {"uuid": _required_uuid("BAZA_MATRIX_B_UUID"), "port": 443, "flow": VISION_FLOW, "email": "matrix-b-443-vision"},
        "C": {"uuid": _required_uuid("BAZA_MATRIX_C_UUID"), "port": 8443, "flow": None, "email": "matrix-c-8443-no-flow"},
        "D": {"uuid": _required_uuid("BAZA_MATRIX_D_UUID"), "port": 8443, "flow": VISION_FLOW, "email": "matrix-d-8443-vision"},
    }

    original = CONFIG_PATH.read_text()
    data = json.loads(original)
    inbounds = data.setdefault("inbounds", [])
    source = next(
        inbound
        for inbound in inbounds
        if inbound.get("protocol") == "vless" and inbound.get("port") in {443, 8443}
    )
    source_8443 = next(
        (inbound for inbound in inbounds if inbound.get("protocol") == "vless" and inbound.get("port") == 8443),
        source,
    )

    inbound_443 = _ensure_inbound(inbounds, port=443, tag=INBOUND_443_TAG, source=source_8443)
    inbound_8443 = _ensure_inbound(inbounds, port=8443, tag=source_8443.get("tag") or "vless-reality-8443", source=source_8443)

    clients_by_port = {
        443: inbound_443.setdefault("settings", {}).setdefault("clients", []),
        8443: inbound_8443.setdefault("settings", {}).setdefault("clients", []),
    }
    for item in matrix.values():
        _upsert_client(
            clients_by_port[item["port"]],
            client_id=item["uuid"],
            email=item["email"],
            flow=item["flow"],
        )

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
    print(
        "matrix=",
        [
            {
                "code": code,
                "port": item["port"],
                "has_flow": bool(item["flow"]),
                "credential_sha256_12": _sha12(item["uuid"]),
            }
            for code, item in matrix.items()
        ],
    )
    print(
        "inbounds=",
        [
            {
                "tag": inbound.get("tag"),
                "port": inbound.get("port"),
                "clients": [
                    {"email": client.get("email"), "has_flow": bool(client.get("flow"))}
                    for client in inbound.get("settings", {}).get("clients", [])
                ],
            }
            for inbound in inbounds
            if inbound.get("protocol") == "vless"
        ],
    )


if __name__ == "__main__":
    main()
