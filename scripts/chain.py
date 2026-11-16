"""StudioNet client helpers. Persist each transaction hash before polling."""

import importlib.metadata
import json
import os
import re
import time
from pathlib import Path

from eth_account import Account
from genlayer_py import create_client, studionet
from genlayer_py.provider import provider
from genlayer_py.types import TransactionHashVariant

ROOT = Path(__file__).resolve().parent.parent
assert importlib.metadata.version("genlayer-py") == "0.18.0"
UA = {"User-Agent": "Mozilla/5.0 BountyBench/1.0"}


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        raise RuntimeError("Missing ignored .env containing the six demo keys")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()

_post = provider.requests.post


def browser_post(url, **kwargs):
    kwargs["headers"] = {**kwargs.get("headers", {}), **UA}
    kwargs.setdefault("timeout", 45)
    method = kwargs.get("json", {}).get("method", "")
    safe = method.startswith(("eth_get", "gen_get", "sim_get")) or method in (
        "eth_chainId",
        "gen_call",
    )
    for attempt in range(4 if safe else 1):
        try:
            response = _post(url, **kwargs)
            if response.status_code not in (429, 502, 503, 504) or not safe or attempt == 3:
                return response
        except provider.requests.exceptions.RequestException:
            if not safe or attempt == 3:
                raise
        print("Transient read-only RPC failure; retrying", flush=True)
        time.sleep(5 * (attempt + 1))


provider.requests.post = browser_post


def accounts():
    names = ["FUNDER", "HUNTER_A", "HUNTER_B", "HUNTER_C", "HUNTER_D", "HUNTER_E"]
    result = []
    for name in names:
        key = os.environ.get(name + "_PRIVATE_KEY", "")
        if not re.fullmatch(r"0x[0-9a-fA-F]{64}", key):
            raise RuntimeError("Missing or malformed " + name + "_PRIVATE_KEY in ignored .env")
        result.append(Account.from_key(key))
    return result


def client(index=0):
    return create_client(chain=studionet, account=accounts()[index])


def load_proof():
    path = ROOT / "deploy/proof.json"
    return json.loads(path.read_text(encoding="utf-8"))


def save_proof(proof):
    target = ROOT / "deploy/proof.json"
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    temp.replace(target)


def success(receipt):
    leader = ((receipt.get("consensus_data") or {}).get("leader_receipt") or [{}])[0]
    native = receipt.get("value_credited") is True and str(receipt.get("type")) == "0" and not receipt.get("consensus_data")
    executed = receipt.get("txExecutionResultName", leader.get("execution_result")) in (
        "SUCCESS",
        "FINISHED_WITH_RETURN",
    ) and receipt.get("result_name") not in ("DISAGREE", "MAJORITY_DISAGREE")
    return receipt.get("status_name", receipt.get("status")) in ("FINALIZED", 7, "7") and (native or executed)


def final(hash_value, label, allow_error=False, poll_seconds=10, attempts=360):
    target = ROOT / "deploy/receipts" / (label + ".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(attempts):
        result = client().provider.make_request("eth_getTransactionByHash", [hash_value])["result"]
        status = result.get("status_name", result.get("status")) if result else None
        if result and status in ("CANCELED", 8, "8"):
            target.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(label, "CANCELED", hash_value, flush=True)
            if not allow_error:
                raise RuntimeError("Transaction canceled before consensus; inspect " + str(target))
            return result
        if result and status in ("FINALIZED", 7, "7"):
            target.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(label, "FINALIZED_SUCCESS" if success(result) else "FINALIZED_ERROR", hash_value, flush=True)
            if not success(result) and not allow_error:
                raise RuntimeError("Execution failed; inspect " + str(target))
            return result
        if attempt % max(1, 60 // poll_seconds) == 0:
            state = result.get("status_name", result.get("status")) if result else "SUBMITTED"
            print(label, state, flush=True)
        time.sleep(poll_seconds)
    raise RuntimeError("Still pending; rerun to resume " + hash_value)


def tx(proof, label, address=None, method=None, args=None, code=None, index=0, value=0, allow_error=False, wait=True):
    if label not in proof["transactions"]:
        marker = ROOT / "deploy/.pending-write.json"
        if marker.exists():
            raise RuntimeError("Reconcile ambiguous submission before any new write: " + str(marker))
        deposit_groups = [proof.get("deposits", {})]
        deposit_groups.extend(
            release.get("deposits", {})
            for release in proof.get("releases", {}).values()
        )
        total = sum(int(amount) for group in deposit_groups for amount in group.values())
        if value and total + int(value) > int(proof["approvedTotalWei"]):
            raise RuntimeError("Cumulative payable calls exceed the approved wei budget")
        marker.write_text(
            json.dumps({"label": label, "address": address, "method": method, "valueWei": int(value)}),
            encoding="utf-8",
        )
        instance = client(index)
        fees = {"feeValue": 0}
        handle = (
            instance.deploy_contract(code, args=args or [], fees=fees)
            if code is not None
            else instance.write_contract(address, method, args=args or [], value=int(value), fees=fees)
        )
        tx_hash = handle.hex() if hasattr(handle, "hex") else str(handle)
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash
        proof["transactions"][label] = tx_hash
        if value:
            proof.setdefault("deposits", {})[label] = int(value)
        save_proof(proof)
        marker.unlink()
        print(label, "SUBMITTED", tx_hash, flush=True)
    tx_hash = proof["transactions"][label]
    if not wait:
        return {"hash": tx_hash, "status": "SUBMITTED"}
    receipt = final(tx_hash, label, allow_error=allow_error)
    if not success(receipt):
        proof.setdefault("nonSuccessfulTransactions", {})[label] = {
            "status": receipt.get("status_name", receipt.get("status")),
            "result": receipt.get("result_name", ""),
        }
        save_proof(proof)
    _follow_children(proof, label, receipt, allow_error=allow_error)
    return receipt


def _follow_children(proof, parent_label, receipt, allow_error=False, depth=0):
    if depth >= 12:
        raise RuntimeError("Cross-contract transaction tree exceeded 12 levels")
    for child_index, child_hash in enumerate(receipt.get("triggered_transactions") or []):
        child_label = parent_label + "-child-" + str(child_index)
        existing = proof["transactions"].get(child_label)
        if existing and existing.lower() != child_hash.lower():
            raise RuntimeError("Triggered transaction hash changed for " + child_label)
        proof["transactions"].setdefault(child_label, child_hash)
        save_proof(proof)
        child_receipt = final(child_hash, child_label, allow_error=True)
        if not success(child_receipt):
            proof.setdefault("nonSuccessfulTransactions", {})[child_label] = {
                "status": child_receipt.get("status_name", child_receipt.get("status")),
                "result": child_receipt.get("result_name", ""),
            }
            save_proof(proof)
        _follow_children(proof, child_label, child_receipt, allow_error=allow_error, depth=depth + 1)


def read(address, method, args=None):
    result = client().read_contract(
        address,
        method,
        args=args or [],
        transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
    )
    time.sleep(5)
    return json.loads(result) if isinstance(result, str) and result.startswith(("{", "[")) else result

