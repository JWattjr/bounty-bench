"""Resumable StudioNet contract deployment and live Bounty Bench cases."""

import hashlib
import json
import sys
import time
from pathlib import Path

from chain import ROOT, load_proof, read, save_proof, success, tx


REPO = "JWattjr/bounty-bench-fixtures"
FIXTURE_PATH = ROOT / "deploy/fixture.json"
PROOF = load_proof()
CRITERIA = [
    "changes `normalize_slug` so that it collapses repeated hyphens",
    "changes `normalize_slug` so that it trims hyphens at both ends",
    "adds a test that exercises `normalize_slug` with repeated hyphens and asserts that they collapse",
]


def save():
    save_proof(PROOF)


def address(name):
    return PROOF["contracts"][name]["address"]


def fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def record_action(bounty_id, action, hash_label, tx_label=None, board_address=None):
    label = tx_label or "record-" + action.replace(":", "-")
    tx(
        PROOF,
        label,
        board_address or address("BountyBoard"),
        "record_transaction",
        [bounty_id, action, PROOF["transactions"][hash_label]],
    )


def create_bounty(name, bounty_id, title, criteria, reward, deadline, bond, transaction_label=None):
    case = PROOF.setdefault("cases", {}).setdefault(name, {})
    case.update({
        "bountyId": bounty_id,
        "repo": REPO,
        "baseSha": fixture()["baseSha"],
        "title": title,
        "criteria": criteria,
        "deadline": deadline,
        "claimBondWei": bond,
        "rewardWei": reward,
    })
    save()
    label = transaction_label or "create-" + name
    tx(
        PROOF,
        label,
        address("BountyBoard"),
        "create_bounty",
        [REPO, fixture()["baseSha"], title, json.dumps(criteria, separators=(",", ":")), deadline, bond],
        index=0,
        value=reward,
    )
    current = read(address("BountyBoard"), "get_bounty", [bounty_id])
    case["createdStatus"] = current.get("status", "")
    save()
    allowed = ("SPEC_REJECTED", "REJECT_REFUND_PENDING", "REJECTED_REFUNDED") if name == "rejected" else (
        "OPEN", "REFUNDED_INVALID", "REWARD_REFUND_PENDING", "CLOSED", "AWARD_PENDING"
    )
    if current.get("status") not in allowed:
        raise RuntimeError(name + " did not reach an expected compiled or settled state: " + current.get("status", "missing"))
    record_action(bounty_id, "board:create-" + name, "create-" + name)
    compile_label = label + "-child-0"
    if compile_label in PROOF["transactions"]:
        record_action(bounty_id, "judge:compile-" + name, compile_label)
    return case


def rejected_case():
    case = PROOF.setdefault("cases", {}).setdefault("rejected", {})
    if "deadline" not in case:
        case["deadline"] = int(time.time()) + 7200
    create_bounty(
        "rejected",
        "bounty-1",
        "A deliberately vague code bounty",
        ["make the code cleaner and well tested"],
        15,
        case["deadline"],
        5,
    )
    tx(PROOF, "refund-rejected", address("BountyBoard"), "refund_rejected", ["bounty-1"])
    record_action("bounty-1", "board:refund-rejected", "refund-rejected")
    bounty = read(address("BountyBoard"), "get_bounty", ["bounty-1"])
    if bounty.get("status") != "REJECTED_REFUNDED" or bounty.get("reward_remaining_wei") != "0":
        raise RuntimeError("Rejected-spec reward was not returned")
    case["finalStatus"] = bounty["status"]
    case["refundWei"] = "15"
    save()


def timeout_case():
    case = PROOF.setdefault("cases", {}).setdefault("timeout", {})
    current_id = case.get("bountyId", "bounty-2")
    if "create-timeout" in PROOF["transactions"] and case.get("createdStatus") == "REFUNDED_INVALID" and "create-timeout-replacement" not in PROOF["transactions"]:
        case.setdefault("attempts", []).append({
            "bountyId": current_id,
            "transaction": PROOF["transactions"]["create-timeout"],
            "status": "REFUNDED_INVALID",
            "rewardWei": "20",
            "reason": "The exact 60-minute local deadline was slightly short against the StudioNet block clock; the contract refunded the reward.",
        })
        case["deadline"] = int(time.time()) + 3900
        case["bountyId"] = "bounty-3"
        save()
        create_bounty(
            "timeout",
            "bounty-3",
            "A bounty that closes without claims",
            ["changes `normalize_slug` so that it trims hyphens at both ends"],
            20,
            case["deadline"],
            5,
            transaction_label="create-timeout-replacement",
        )
    elif "create-timeout-replacement" not in PROOF["transactions"] and "create-timeout" not in PROOF["transactions"]:
        if "deadline" not in case:
            case["deadline"] = int(time.time()) + 3900
        case["bountyId"] = "bounty-2"
        create_bounty(
            "timeout",
            case["bountyId"],
            "A bounty that closes without claims",
            ["changes `normalize_slug` so that it trims hyphens at both ends"],
            20,
            case["deadline"],
            5,
        )
    deadline = int(case["deadline"])
    if int(time.time()) < deadline + 1800:
        case["finalStatus"] = "WAITING_FOR_DEADLINE_GRACE"
        case["eligibleAt"] = deadline + 1800
        save()
        print("Timeout case remains open until", time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(deadline + 1800)), flush=True)
        return
    bounty_id = case.get("bountyId", "bounty-2")
    tx(PROOF, "close-timeout", address("BountyBoard"), "close", [bounty_id])
    record_action(bounty_id, "board:close-timeout", "close-timeout")
    bounty = read(address("BountyBoard"), "get_bounty", [bounty_id])
    if bounty.get("status") != "CLOSED" or bounty.get("reward_remaining_wei") != "0":
        raise RuntimeError("Timeout bounty did not close and refund its reward")
    case["finalStatus"] = bounty["status"]
    case["closedAt"] = bounty.get("closed_at")
    save()


def main_case():
    case = PROOF.setdefault("cases", {}).setdefault("main", {})
    timeout_case = PROOF.get("cases", {}).get("timeout")
    next_id = int(timeout_case["bountyId"].rsplit("-", 1)[-1]) + 1 if timeout_case else 1
    bounty_id = case.get("bountyId", "bounty-" + str(next_id))
    case["bountyId"] = bounty_id
    if "deadline" not in case:
        case["deadline"] = int(time.time()) + 24 * 3600
    data = fixture()
    create_bounty(
        "main",
        bounty_id,
        "Collapse and trim slug separators, with a regression test",
        CRITERIA,
        50,
        case["deadline"],
        5,
    )
    branches = data["branches"]
    hunters = data["wallets"]
    order = [
        ("A", 1, branches["hunter-a"]),
        ("B", 2, branches["hunter-b"]),
        ("C", 3, branches["hunter-c"]),
        ("D", 4, branches["hunter-d"]),
        ("E", 5, branches["hunter-e"]),
    ]
    claims = case.setdefault("claims", {})
    for letter, account_index, head_sha in order:
        label = "claim-" + letter
        claim_id = "claim-" + str(account_index)
        claims.setdefault(letter, {"id": claim_id, "headSha": head_sha, "hunter": hunters["hunter-" + letter.lower()]})
        save()
        tx(PROOF, label, address("BountyBoard"), "claim", [bounty_id, head_sha], index=account_index, value=5)
        record_action(bounty_id, "board:claim-" + letter, label)
        stored = read(address("BountyBoard"), "get_claims", [bounty_id, 0, 50])
        found = next((item for item in stored if item.get("id") == claim_id), None)
        if not found:
            raise RuntimeError("Claim was not stored in the expected queue slot: " + claim_id)
        claims[letter]["identityStatus"] = found.get("identity_status", "")
        claims[letter]["status"] = found.get("status", "")
        save()

    expected = [
        ("B", 0, "MET"), ("B", 1, "MET"), ("B", 2, "NOT_MET"),
        ("C", 0, "NOT_MET"),
        ("D", 0, "MET"), ("D", 1, "MET"), ("D", 2, "MET"),
    ]
    for letter, criterion_index, expected_verdict in expected:
        claim_id = claims[letter]["id"]
        base_label = "judge-" + letter + "-c" + str(criterion_index)
        retry = 0
        while True:
            stored = read(address("BountyBoard"), "get_claims", [bounty_id, 0, 50])
            claim = next(item for item in stored if item.get("id") == claim_id)
            prior = next((item for item in claim.get("verdicts", []) if int(item.get("criterion_index", -1)) == criterion_index), None)
            if prior:
                break
            if claim.get("status") == "JUDGING":
                retry_after = int(claim.get("judging_started_at", 0)) + 305
                remaining = retry_after - int(time.time())
                if remaining > 0:
                    print("Waiting for stale judgment recovery", letter, criterion_index, remaining, "seconds", flush=True)
                    time.sleep(min(30, remaining))
                    continue
            if claim.get("status") not in ("PENDING", "JUDGING"):
                raise RuntimeError(base_label + " ended in " + str(claim.get("status")) + " without a verdict")
            label = base_label if retry == 0 else base_label + "-retry-" + str(retry)
            receipt = tx(PROOF, label, address("BountyBoard"), "judge_next", [bounty_id], index=1)
            record_action(bounty_id, "board:" + label, label)
            judge_child = label + "-child-0"
            if judge_child in PROOF["transactions"]:
                if judge_child not in PROOF.get("nonSuccessfulTransactions", {}):
                    record_action(bounty_id, "judge:" + label, judge_child)
            elif success(receipt):
                # The Board may settle a repeated consensus failure directly without a PatchJudge child.
                pass
            retry += 1
            if retry > 4:
                raise RuntimeError(base_label + " did not produce a finalized verdict after recovery attempts")
        actual = prior.get("verdict")
        if actual != expected_verdict:
            raise RuntimeError(base_label + " finalized " + str(actual) + "; expected " + expected_verdict)
        claims[letter]["status"] = claim.get("status", "")
        claims[letter]["verdicts"] = claim.get("verdicts", [])
        save()

    stored = read(address("BountyBoard"), "get_claims", [bounty_id, 0, 50])
    states = {item["id"]: item for item in stored}
    bounty = read(address("BountyBoard"), "get_bounty", [bounty_id])
    balances = read(address("BountyBoard"), "get_balances", [bounty_id])
    expectations = {
        "claim-1": "IDENTITY_MISMATCH",
        "claim-2": "FAILED",
        "claim-3": "FAILED",
        "claim-4": "WON",
        "claim-5": "REFUNDED_AFTER_WIN",
    }
    for claim_id, status in expectations.items():
        if states[claim_id].get("status") != status:
            raise RuntimeError(claim_id + " ended as " + states[claim_id].get("status", "missing") + "; expected " + status)
    if bounty.get("status") != "CLOSED" or bounty.get("winner_id") != "claim-4":
        raise RuntimeError("First fully valid claim did not close the bounty")
    if int(balances.get("reward_remaining_wei", "-1")) != 0:
        raise RuntimeError("Winner reward remains in escrow")
    if int(balances.get("forfeited_bonds_wei", "-1")) != 15:
        raise RuntimeError("The three rejected bonds did not reach the funder")
    case["finalStatus"] = bounty["status"]
    case["winner"] = claims["D"]["hunter"]
    case["finalClaims"] = states
    case["balances"] = balances
    save()


def deploy_contracts():
    for name, filename, args in [
        ("BountyBoard", "bounty_board.py", []),
        ("PatchJudge", "patch_judge.py", None),
    ]:
        source_path = ROOT / "contracts" / filename
        source = source_path.read_text(encoding="utf-8")
        source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if name in PROOF["contracts"]:
            if PROOF["contracts"][name]["sha256"] != source_sha:
                raise RuntimeError(name + " source differs from the deployed source; use a new deployment")
            continue
        deploy_args = args if args is not None else [address("BountyBoard")]
        receipt = tx(PROOF, "deploy-" + name, code=source, args=deploy_args, index=0)
        deployed_address = receipt.get("recipient", receipt.get("to_address"))
        if not deployed_address:
            raise RuntimeError(name + " deployment finalized without a contract address")
        PROOF["contracts"][name] = {"address": deployed_address, "source": filename, "sha256": source_sha}
        save()
    tx(PROOF, "configure-patch-judge", address("BountyBoard"), "set_patch_judge", [address("PatchJudge")])
    PROOF["releaseStatus"] = "CONTRACTS_DEPLOYED"
    save()


def archive_v1():
    releases = PROOF.setdefault("releases", {})
    if "v1" in releases:
        return
    old_contracts = {
        name: PROOF["contracts"][name]
        for name in ("BountyBoard", "PatchJudge")
        if name in PROOF.get("contracts", {})
    }
    old_non_success = dict(PROOF.get("nonSuccessfulTransactions", {}))
    canceled_child = PROOF.get("transactions", {}).get("judge-D-c2-child-0")
    if canceled_child:
        old_non_success.setdefault("judge-D-c2-child-0", {
            "status": "CANCELED",
            "result": "NO_MAJORITY",
            "reason": "StudioNet validators exhausted recovery cycles; the immutable v1 Board had no stale-judgment reset.",
        })
    releases["v1"] = {
        "releaseStatus": PROOF.get("releaseStatus", "UNKNOWN"),
        "contracts": old_contracts,
        "cases": PROOF.get("cases", {}),
        "transactions": PROOF.get("transactions", {}),
        "deposits": PROOF.get("deposits", {}),
        "nonSuccessfulTransactions": old_non_success,
    }
    PROOF["retiredContracts"] = {
        "BountyBoard-v1": {
            **old_contracts["BountyBoard"],
            "source": "archive/bounty_board_v1.py",
            "release": "v1",
        },
        "PatchJudge-v1": {
            **old_contracts["PatchJudge"],
            "source": "archive/patch_judge_v1.py",
            "release": "v1",
        },
    }
    PROOF["contracts"] = {
        name: contract
        for name, contract in PROOF.get("contracts", {}).items()
        if name not in ("BountyBoard", "PatchJudge")
    }
    PROOF["transactions"] = {}
    PROOF["deposits"] = {}
    PROOF["nonSuccessfulTransactions"] = {}
    PROOF["cases"] = {}
    PROOF["releaseStatus"] = "MIGRATING_V2"
    save()


def archive_active_release(version):
    releases = PROOF.setdefault("releases", {})
    if version in releases:
        return
    old_contracts = {
        name: PROOF["contracts"][name]
        for name in ("BountyBoard", "PatchJudge")
        if name in PROOF.get("contracts", {})
    }
    archived_contracts = {}
    for name, contract in old_contracts.items():
        filename = "bounty_board" if name == "BountyBoard" else "patch_judge"
        archived_contracts[name] = {
            **contract,
            "source": "archive/" + filename + "_" + version + ".py",
            "release": version,
        }
    releases[version] = {
        "releaseStatus": PROOF.get("releaseStatus", "UNKNOWN"),
        "outcomeSummary": "The main claim reached INSUFFICIENT_EVIDENCE after PatchJudge returned LLM_ERROR for the regression-test criterion; reward remained escrowed.",
        "contracts": archived_contracts,
        "cases": PROOF.get("cases", {}),
        "transactions": PROOF.get("transactions", {}),
        "deposits": PROOF.get("deposits", {}),
        "nonSuccessfulTransactions": PROOF.get("nonSuccessfulTransactions", {}),
    }
    retired = PROOF.setdefault("retiredContracts", {})
    for name, contract in archived_contracts.items():
        retired[name + "-" + version] = contract
    PROOF["contracts"] = {
        name: contract
        for name, contract in PROOF.get("contracts", {}).items()
        if name not in ("BountyBoard", "PatchJudge")
    }
    PROOF["transactions"] = {}
    PROOF["deposits"] = {}
    PROOF["nonSuccessfulTransactions"] = {}
    PROOF["cases"] = {}
    PROOF["releaseStatus"] = "MIGRATING_" + version.upper()
    save()


def close_archived_cases():
    for release_name, release in PROOF.get("releases", {}).items():
        old_board = release.get("contracts", {}).get("BountyBoard", {}).get("address")
        if not old_board:
            continue
        for case_name, case in release.get("cases", {}).items():
            bounty_id = case.get("bountyId")
            if not bounty_id or case.get("finalStatus") in (
                "CLOSED", "REJECTED_REFUNDED", "REFUNDED_INVALID"
            ):
                continue
            deadline = int(case.get("deadline", 0))
            eligible_at = deadline + 1800
            if not deadline or int(time.time()) < eligible_at:
                case["cleanupStatus"] = "WAITING_FOR_DEADLINE_GRACE"
                case["cleanupEligibleAt"] = eligible_at if deadline else None
                save()
                continue
            label = "close-" + release_name + "-" + case_name
            tx(PROOF, label, old_board, "close", [bounty_id])
            record_action(
                bounty_id,
                "board:close-" + release_name + "-" + case_name,
                label,
                board_address=old_board,
            )
            bounty = read(old_board, "get_bounty", [bounty_id])
            if bounty.get("status") != "CLOSED" or bounty.get("reward_remaining_wei") != "0":
                raise RuntimeError(release_name + " " + case_name + " did not close and refund its remaining reward")
            case["finalStatus"] = "CLOSED"
            case["closedAt"] = bounty.get("closed_at")
            case["cleanupStatus"] = "CLOSED"
            case.pop("cleanupEligibleAt", None)
            save()


def deploy_replacement_contracts(version=2):
    if version == 2:
        archive_v1()
    else:
        archive_active_release("v" + str(version - 1))
    for name, filename, args in [
        ("BountyBoard", "bounty_board.py", []),
        ("PatchJudge", "patch_judge.py", None),
    ]:
        source_path = ROOT / "contracts" / filename
        source = source_path.read_text(encoding="utf-8")
        source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
        current = PROOF.get("contracts", {}).get(name)
        if current:
            if current["sha256"] != source_sha:
                raise RuntimeError(name + " source differs from the replacement deployment")
            continue
        deploy_args = args if args is not None else [address("BountyBoard")]
        receipt = tx(PROOF, "deploy-v" + str(version) + "-" + name, code=source, args=deploy_args, index=0)
        deployed_address = receipt.get("recipient", receipt.get("to_address"))
        if not deployed_address:
            raise RuntimeError(name + " replacement deployment finalized without a contract address")
        PROOF["contracts"][name] = {"address": deployed_address, "source": filename, "sha256": source_sha}
        save()
    tx(PROOF, "configure-v" + str(version) + "-patch-judge", address("BountyBoard"), "set_patch_judge", [address("PatchJudge")])
    PROOF["releaseStatus"] = "CONTRACTS_DEPLOYED"
    save()


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage == "redeploy-v2":
        deploy_replacement_contracts(2)
    if stage == "redeploy-v3":
        deploy_replacement_contracts(3)
    if stage in ("deploy", "all"):
        deploy_contracts()
    if stage in ("cases", "all"):
        rejected_case()
        timeout_case()
        main_case()
        timeout_closed = PROOF.get("cases", {}).get("timeout", {}).get("finalStatus") == "CLOSED"
        PROOF["releaseStatus"] = "LIVE_CASES_COMPLETE" if timeout_closed else "LIVE_MAIN_COMPLETE_TIMEOUT_PENDING"
        save()
    if stage == "timeout":
        timeout_case()
        if PROOF["cases"].get("timeout", {}).get("finalStatus") == "CLOSED":
            main_closed = PROOF.get("cases", {}).get("main", {}).get("finalStatus") == "CLOSED"
            PROOF["releaseStatus"] = "LIVE_CASES_COMPLETE" if main_closed else "LIVE_TIMEOUT_COMPLETE_MAIN_PENDING"
            save()
    if stage == "close-legacy":
        close_archived_cases()
    if stage not in ("all", "deploy", "cases", "timeout", "redeploy-v2", "redeploy-v3", "close-legacy"):
        raise SystemExit("Usage: python scripts/release.py [deploy|cases|timeout|redeploy-v2|redeploy-v3|close-legacy|all]")


if __name__ == "__main__":
    main()
