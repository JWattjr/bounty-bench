"""Fund six ignored demo accounts from the explicitly approved StudioNet source."""

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from chain import ROOT, accounts, load_proof, save_proof

FUNDING_PATH = ROOT / "deploy/funding.json"
SOURCE = "moment-grid-studionet"
PLAN = (
    [("funder", 0, 85)]
    + [("hunter_" + letter.lower(), index, 5) for index, letter in enumerate("ABCDE", 1)]
    + [("funder_v2", 0, 85)]
    + [("hunter_" + letter.lower() + "_v2", index, 5) for index, letter in enumerate("ABCDE", 1)]
    + [("funder_v3", 0, 25)]
    + [("hunter_" + letter.lower() + "_v3", index, 5) for letter, index in [("A", 1), ("B", 2), ("C", 3), ("E", 5)]]
)
HASH_PATTERN = re.compile(r"0x[0-9a-fA-F]{64}")


def cli_command(*args):
    executable = shutil.which("genlayer.cmd") or shutil.which("genlayer")
    if not executable:
        raise RuntimeError("GenLayer CLI shim was not found on PATH")
    if executable.lower().endswith((".cmd", ".bat")):
        shell = shutil.which("cmd.exe") or "cmd.exe"
        command = subprocess.list2cmdline([executable, *args])
        return [shell, "/d", "/s", "/c", command]
    return [executable, *args]


def save_funding(data):
    temp = FUNDING_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(FUNDING_PATH)


def run_transfer(label, address, amount, data, proof):
    recorded = data["transfers"].get(label)
    if recorded and recorded.get("transactionHash"):
        print(label, "already recorded", recorded["transactionHash"], flush=True)
        return

    intent = ROOT / "deploy/.funding-intent.json"
    if intent.exists():
        previous = json.loads(intent.read_text(encoding="utf-8"))
        raise RuntimeError("Reconcile the saved funding intent before any new transfer: " + previous.get("label", "unknown"))
    intent.write_text(
        json.dumps({"label": label, "to": address, "wei": amount, "source": SOURCE}),
        encoding="utf-8",
    )

    process = subprocess.Popen(
        cli_command("account", "send", address, str(amount), "--account", SOURCE),
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    # The source account is pre-unlocked. This answers only a CLI confirmation prompt.
    if process.stdin:
        process.stdin.write("y\n")
        process.stdin.flush()
        process.stdin.close()

    tx_hash = None
    tail = []
    assert process.stdout is not None
    for line in process.stdout:
        # Keep diagnostics bounded and never echo raw command output to the console.
        tail.append(line.strip()[:240])
        tail = tail[-8:]
        if tx_hash is None:
            found = HASH_PATTERN.search(line)
            if found:
                tx_hash = found.group(0)
                data["transfers"][label] = {
                    "to": address,
                    "wei": amount,
                    "transactionHash": tx_hash,
                    "status": "SUBMITTED",
                }
                save_funding(data)
                proof["transactions"]["funding-" + label] = tx_hash
                save_proof(proof)
                print(label, "SUBMITTED", tx_hash, flush=True)

    exit_code = process.wait(timeout=300)
    if not tx_hash:
        intent.write_text(
            json.dumps({"label": label, "to": address, "wei": amount, "source": SOURCE, "outputTail": tail}),
            encoding="utf-8",
        )
        raise RuntimeError("Funding command returned no transaction hash; saved intent and bounded diagnostics")
    if exit_code != 0:
        print(label, "CLI exited", exit_code, "after recording hash; resuming from the saved hash", flush=True)

    intent.unlink(missing_ok=True)
    # Do not rebroadcast if this poll is interrupted: the hash is already in both manifests.
    from chain import final

    receipt = final(tx_hash, "funding-" + label, attempts=360, poll_seconds=10)
    if not receipt.get("value_credited") is True or int(receipt.get("value", 0)) != amount:
        raise RuntimeError("Source transfer finalized without the expected native credit")
    data["transfers"][label]["status"] = "FINALIZED_SUCCESS"
    save_funding(data)


def main():
    data = json.loads(FUNDING_PATH.read_text(encoding="utf-8"))
    proof = load_proof()
    wallets = accounts()
    if sum(amount for _, _, amount in PLAN) != data["plannedTransfersWei"]:
        raise RuntimeError("Funding schedule no longer matches the recorded approved total")
    if data["plannedTransfersWei"] > data["approvedTotalWei"]:
        raise RuntimeError("Source transfers exceed the approved wei budget")
    for label, index, amount in PLAN:
        address = wallets[index].address
        data.setdefault("wallets", {})[label] = address
        save_funding(data)
        run_transfer(label, address, amount, data, proof)
    data["status"] = "FUNDED"
    save_funding(data)
    print("All six demo wallets funded; no private keys were printed.", flush=True)


if __name__ == "__main__":
    main()

