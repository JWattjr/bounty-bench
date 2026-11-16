"""Read-only StudioNet RPC and Explorer verification for deploy/proof.json."""

import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
PROOF = json.loads((ROOT / "deploy/proof.json").read_text(encoding="utf-8"))
RPC = "https://studio.genlayer.com/api"
EXPLORER = "https://explorer-studio.genlayer.com"
HEADERS = {"User-Agent": "Mozilla/5.0 BountyBench/1.0", "Accept": "application/json"}
LAST_REQUEST = 0.0


def get_json(url):
    global LAST_REQUEST
    for attempt in range(5):
        wait = 2.1 - (time.monotonic() - LAST_REQUEST)
        if wait > 0:
            time.sleep(wait)
        try:
            response = requests.get(url, headers=HEADERS, timeout=45)
        except requests.exceptions.RequestException:
            LAST_REQUEST = time.monotonic()
            if attempt == 4:
                raise
            print("Transient Explorer read timeout; retrying", flush=True)
            time.sleep(3 * (attempt + 1))
            continue
        LAST_REQUEST = time.monotonic()
        if response.status_code in (429, 502, 503, 504) and attempt < 4:
            print("Transient Explorer read failure; retrying", flush=True)
            time.sleep(3 * (attempt + 1))
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError("Explorer read retries exhausted")


def get_page(url):
    global LAST_REQUEST
    for attempt in range(5):
        wait = 2.1 - (time.monotonic() - LAST_REQUEST)
        if wait > 0:
            time.sleep(wait)
        try:
            response = requests.get(url, headers=HEADERS, timeout=45)
        except requests.exceptions.RequestException:
            LAST_REQUEST = time.monotonic()
            if attempt == 4:
                raise
            print("Transient Explorer page timeout; retrying", flush=True)
            time.sleep(3 * (attempt + 1))
            continue
        LAST_REQUEST = time.monotonic()
        if response.status_code in (429, 502, 503, 504) and attempt < 4:
            print("Transient Explorer page failure; retrying", flush=True)
            time.sleep(3 * (attempt + 1))
            continue
        response.raise_for_status()
        return response
    raise RuntimeError("Explorer page retries exhausted")


def rpc(method, params):
    global LAST_REQUEST
    for attempt in range(5):
        wait = 2.1 - (time.monotonic() - LAST_REQUEST)
        if wait > 0:
            time.sleep(wait)
        try:
            response = requests.post(
                RPC,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                headers=HEADERS,
                timeout=45,
            )
        except requests.exceptions.RequestException:
            LAST_REQUEST = time.monotonic()
            if attempt == 4:
                raise
            print("Transient StudioNet RPC read timeout; retrying", flush=True)
            time.sleep(3 * (attempt + 1))
            continue
        LAST_REQUEST = time.monotonic()
        if response.status_code in (429, 502, 503, 504) and attempt < 4:
            print("Transient StudioNet RPC response; retrying", flush=True)
            time.sleep(3 * (attempt + 1))
            continue
        response.raise_for_status()
        body = response.json()
        if body.get("error"):
            raise RuntimeError(method + ": " + str(body["error"]))
        return body.get("result")
    raise RuntimeError(method + " RPC retries exhausted")


def nested_address_objects(value):
    if isinstance(value, dict):
        if "type" in value and "address" in value:
            yield value
        for child in value.values():
            yield from nested_address_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_address_objects(child)


def verify_contracts():
    contracts = dict(PROOF.get("contracts", {}))
    contracts.update(PROOF.get("retiredContracts", {}))
    for name, contract in contracts.items():
        address = contract["address"]
        if not re.fullmatch(r"0x[0-9a-fA-F]{40}", address):
            raise RuntimeError(name + " address is malformed")
        source = ROOT / "contracts" / contract["source"]
        actual_sha = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual_sha != contract["sha256"]:
            raise RuntimeError(name + " source no longer matches the deployed manifest hash")
        result = get_json(EXPLORER + "/api/address/" + address)
        matches = [item for item in nested_address_objects(result) if str(item.get("address", "")).lower() == address.lower()]
        if not matches or not any(item.get("type") == "CONTRACT" for item in matches):
            raise RuntimeError(name + " Explorer address endpoint did not return this address as type CONTRACT")
        page_url = EXPLORER + "/address/" + address
        page = get_page(page_url)
        if urlparse(page.url).hostname != "explorer-studio.genlayer.com" or address.lower() not in page.url.lower():
            raise RuntimeError(name + " direct Explorer link did not resolve to this StudioNet address")
        print("CONTRACT", name, address, "direct StudioNet Explorer link and type CONTRACT verified", flush=True)


def verify_transactions():
    chain_id = int(rpc("eth_chainId", []), 16)
    if chain_id != 61999:
        raise RuntimeError("RPC is on chain " + str(chain_id) + ", expected StudioNet 61999")
    groups = [("", PROOF.get("transactions", {}), PROOF.get("nonSuccessfulTransactions", {}))]
    groups.extend(
        (release_name + "/", release.get("transactions", {}), release.get("nonSuccessfulTransactions", {}))
        for release_name, release in PROOF.get("releases", {}).items()
    )
    for prefix, transactions, known_failures in groups:
        for label, tx_hash in transactions.items():
            full_label = prefix + label
            if not re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash):
                raise RuntimeError(full_label + " transaction hash is malformed")
            rpc_tx = rpc("eth_getTransactionByHash", [tx_hash])
            status = rpc_tx.get("status_name", rpc_tx.get("status")) if rpc_tx else None
            expected_failure = known_failures.get(label)
            if expected_failure:
                allowed = expected_failure.get("status")
                if str(status) != str(allowed):
                    raise RuntimeError(full_label + " status is " + str(status) + "; expected recorded " + str(allowed))
            elif status not in ("FINALIZED", 7, "7"):
                raise RuntimeError(full_label + " is not finalized on StudioNet RPC")
            explorer_tx = get_json(EXPLORER + "/api/transactions/" + tx_hash)
            if isinstance(explorer_tx, dict) and explorer_tx.get("error"):
                raise RuntimeError(full_label + " Explorer transaction endpoint returned an error")
            status_text = "recorded " + str(status) if expected_failure else "finalized"
            print("TX", full_label, tx_hash, status_text + " on StudioNet RPC; Explorer transaction endpoint readable", flush=True)


def main():
    if PROOF.get("network") != "StudioNet" or int(PROOF.get("chainId", -1)) != 61999:
        raise RuntimeError("Proof manifest network does not identify StudioNet 61999")
    verify_contracts()
    verify_transactions()
    print("Read-only proof verification passed. No Portal fields were submitted.", flush=True)


if __name__ == "__main__":
    main()
