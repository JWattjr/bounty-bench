# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Open code-bounty escrow, ordered claims, finality settlement, and public proof."""

import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from genlayer import *


RPC_URL = "https://studio.genlayer.com/api"
USER_AGENT = "Mozilla/5.0 BountyBench/1.0"
GRACE_SECONDS = 1800
SETTLE_BATCH = 20
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def require(ok, message):
    if not ok:
        raise gl.vm.UserError("[EXPECTED] " + message)


def now():
    return int(datetime.now(timezone.utc).timestamp())


def canon(value):
    return json.dumps(value, sort_keys=False, separators=(",", ":"), ensure_ascii=False)


def lower_address(value):
    return str(value).lower()


def rpc_transaction(tx_hash):
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionByHash", "params": [tx_hash]}
    response = gl.nondet.web.post(
        RPC_URL,
        body=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    if int(response.status) != 200:
        return {"valid": False, "status": "HTTP_ERROR", "to": ""}
    data = json.loads(response.body.decode("utf-8"))
    item = data.get("result") or {}
    to_address = str(item.get("to_address", "")).lower()
    finalized = item.get("status_name", item.get("status")) in ("FINALIZED", 7, "7")
    executed = item.get("txExecutionResultName") in (None, "SUCCESS", "FINISHED_WITH_RETURN")
    return {"valid": bool(finalized and executed), "status": str(item.get("status_name", item.get("status", ""))), "to": to_address}


def matches_identity_trailer(repo, base_sha, head_sha, hunter):
    url = "https://github.com/" + repo + "/compare/" + base_sha + "..." + head_sha + ".patch"
    try:
        response = gl.nondet.web.get(url, headers={"User-Agent": USER_AGENT})
        status = int(response.status)
        if status != 200:
            return {"status": status, "match": False}
        body = response.body.decode("utf-8", errors="replace")
        expected = ("Bounty-Claimant: " + hunter).lower()
        matched = any(line.strip().lower() == expected for line in body.splitlines())
        return {"status": status, "match": matched}
    except Exception:
        return {"status": 0, "match": False}


@gl.evm.contract_interface
class Recipient:
    class View:
        pass

    class Write:
        pass


class BountyBoard(gl.Contract):
    owner: Address
    patch_judge: Address
    next_bounty: u256
    next_claim: u256
    bounty_ids: DynArray[str]
    bounties: TreeMap[str, str]
    claims: TreeMap[str, str]
    claims_by_bounty: TreeMap[str, str]
    transaction_hashes: TreeMap[str, str]
    transaction_lists: TreeMap[str, str]

    def __init__(self):
        self.owner = gl.message.sender_address
        self.patch_judge = Address(ZERO_ADDRESS)
        self.next_bounty = u256(0)
        self.next_claim = u256(0)

    def _self_only(self):
        require(lower_address(gl.message.sender_address) == lower_address(gl.message.contract_address), "self finality callback only")

    def _get_bounty(self, bounty_id):
        return json.loads(self.bounties.get(bounty_id, "{}"))

    def _put_bounty(self, record):
        self.bounties[record["id"]] = json.dumps(record, sort_keys=True, ensure_ascii=False)

    def _get_claim(self, claim_id):
        return json.loads(self.claims.get(claim_id, "{}"))

    def _put_claim(self, record):
        self.claims[record["id"]] = json.dumps(record, sort_keys=True, ensure_ascii=False)

    def _claim_ids(self, bounty_id):
        return json.loads(self.claims_by_bounty.get(bounty_id, "[]"))

    def _append_claim(self, bounty_id, claim_id):
        ids = self._claim_ids(bounty_id)
        ids.append(claim_id)
        self.claims_by_bounty[bounty_id] = json.dumps(ids)
        bounty = self._get_bounty(bounty_id)
        if bounty:
            bounty["queue_length"] = len(ids)
            self._put_bounty(bounty)

    def _new_claim_id(self):
        number = int(self.next_claim) + 1
        self.next_claim = u256(number)
        return "claim-" + str(number)

    @gl.public.write
    def set_patch_judge(self, judge_address: str) -> None:
        require(lower_address(gl.message.sender_address) == lower_address(self.owner), "owner only")
        require(lower_address(self.patch_judge) == ZERO_ADDRESS, "PatchJudge already configured")
        require(re.fullmatch(r"0x[0-9a-fA-F]{40}", judge_address) is not None, "PatchJudge address required")
        self.patch_judge = Address(judge_address)

    @gl.public.write.payable
    def create_bounty(
        self,
        repo: str,
        base_sha: str,
        title: str,
        criteria_json: str,
        deadline: int,
        claim_bond_wei: int,
    ) -> str:
        value = int(gl.message.value)
        bounty_number = int(self.next_bounty) + 1
        self.next_bounty = u256(bounty_number)
        bounty_id = "bounty-" + str(bounty_number)
        funder = lower_address(gl.message.sender_address)
        raw_criteria = criteria_json if isinstance(criteria_json, str) else ""
        criteria = []
        parsed = False
        try:
            criteria = json.loads(raw_criteria)
            parsed = isinstance(criteria, list)
        except Exception:
            parsed = False
        canonical = canon(criteria) if parsed else raw_criteria[:5000]
        criteria_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        invalid = []
        if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) is None:
            invalid.append("Repository must use owner/name format.")
        if re.fullmatch(r"[0-9a-fA-F]{40}", base_sha) is None:
            invalid.append("Base SHA must contain exactly 40 hexadecimal characters.")
        if not isinstance(title, str) or not 5 <= len(title) <= 140:
            invalid.append("Title must contain 5 to 140 characters.")
        if not parsed or not 1 <= len(criteria) <= 4:
            invalid.append("Provide one to four criteria as a JSON string array.")
        elif any(not isinstance(item, str) or not 5 <= len(item) <= 400 for item in criteria):
            invalid.append("Each criterion must contain 5 to 400 characters.")
        elif len(set(criteria)) != len(criteria):
            invalid.append("Criteria must be unique.")
        if int(deadline) < now() + 3600:
            invalid.append("Deadline must be at least 60 minutes in the future.")
        if int(claim_bond_wei) <= 0:
            invalid.append("Claim bond must be greater than zero wei.")
        if value <= 0:
            invalid.append("Reward must be greater than zero wei.")
        if lower_address(self.patch_judge) == ZERO_ADDRESS:
            invalid.append("PatchJudge is not configured.")
        record = {
            "id": bounty_id,
            "funder": funder,
            "repo": repo,
            "base_sha": base_sha.lower() if isinstance(base_sha, str) else "",
            "title": title,
            "criteria": criteria,
            "criteria_json": canonical,
            "criteria_hash": criteria_hash,
            "criterion_specs": [],
            "spec_results": [],
            "created_at": now(),
            "deadline": int(deadline),
            "claim_bond_wei": str(int(claim_bond_wei)),
            "reward_wei": str(value),
            "reward_remaining_wei": str(value),
            "status": "REFUNDABLE_ERROR" if invalid else "COMPILING",
            "reason": "; ".join(invalid),
            "rejection_reasons": [],
            "queue_length": 0,
            "close_cursor": 0,
            "refund_cursor": 0,
            "winner_id": "",
            "forfeited_bonds_wei": "0",
            "transactions": [],
        }
        self.bounties[bounty_id] = json.dumps(record, sort_keys=True, ensure_ascii=False)
        self.bounty_ids.append(bounty_id)
        self.claims_by_bounty[bounty_id] = "[]"
        if invalid:
            if value > 0:
                gl.get_contract_at(gl.message.contract_address).emit(on="finalized").refund_invalid_reward(bounty_id)
            return bounty_id
        gl.get_contract_at(self.patch_judge).emit(on="finalized").compile_spec(
            bounty_id,
            canonical,
            criteria_hash,
        )
        return bounty_id

    @gl.public.write
    def complete_spec(self, bounty_id: str, status: str, result_json: str) -> None:
        require(lower_address(gl.message.sender_address) == lower_address(self.patch_judge), "PatchJudge only")
        record = self._get_bounty(bounty_id)
        require(record.get("status") == "COMPILING", "bounty is not compiling")
        result = json.loads(result_json)
        require(status in ("SPEC_ACCEPTED", "SPEC_REJECTED") and result.get("status") == status, "invalid spec result")
        record["spec_results"] = result.get("results", [])
        record["criterion_specs"] = [
            {"kind": item.get("kind", "invalid"), "target": item.get("target", ""), "behavior": item.get("behavior", "")}
            for item in record["spec_results"]
        ]
        record["status"] = "OPEN" if status == "SPEC_ACCEPTED" else "SPEC_REJECTED"
        record["rejection_reasons"] = [item.get("reason", "") for item in record["spec_results"] if not item.get("accepted")]
        record["reason"] = "" if status == "SPEC_ACCEPTED" else "One or more acceptance criteria were not observable in a code diff."
        self._put_bounty(record)

    @gl.public.write
    def refund_rejected(self, bounty_id: str) -> None:
        record = self._get_bounty(bounty_id)
        require(record.get("status") == "SPEC_REJECTED", "rejected bounty required")
        require(lower_address(gl.message.sender_address) == record.get("funder"), "funder only")
        if int(record.get("reward_remaining_wei", "0")) <= 0:
            return
        record["status"] = "REJECT_REFUND_PENDING"
        self._put_bounty(record)
        gl.get_contract_at(gl.message.contract_address).emit(on="finalized").pay_rejected_reward(bounty_id)

    @gl.public.write
    def pay_rejected_reward(self, bounty_id: str) -> None:
        self._self_only()
        record = self._get_bounty(bounty_id)
        if record.get("status") != "REJECT_REFUND_PENDING":
            return
        amount = int(record.get("reward_remaining_wei", "0"))
        record["reward_remaining_wei"] = "0"
        record["status"] = "REJECTED_REFUNDED"
        self._put_bounty(record)
        if amount:
            Recipient(Address(record["funder"])).emit_transfer(value=u256(amount), on="finalized")

    @gl.public.write
    def refund_invalid_reward(self, bounty_id: str) -> None:
        self._self_only()
        record = self._get_bounty(bounty_id)
        if record.get("status") != "REFUNDABLE_ERROR":
            return
        amount = int(record.get("reward_remaining_wei", "0"))
        record["reward_remaining_wei"] = "0"
        record["status"] = "REFUNDED_INVALID"
        self._put_bounty(record)
        if amount:
            Recipient(Address(record["funder"])).emit_transfer(value=u256(amount), on="finalized")

    @gl.public.write.payable
    def claim(self, bounty_id: str, head_sha: str) -> str:
        value = int(gl.message.value)
        claimant = lower_address(gl.message.sender_address)
        claim_id = self._new_claim_id()
        bounty = self._get_bounty(bounty_id)
        reason = ""
        if not bounty:
            reason = "Bounty does not exist."
        elif bounty.get("status") != "OPEN":
            reason = "Bounty is not open for claims."
        elif now() >= int(bounty.get("deadline", 0)):
            reason = "Bounty deadline has passed."
        elif value != int(bounty.get("claim_bond_wei", "0")):
            reason = "Claim bond does not match the frozen amount."
        elif re.fullmatch(r"[0-9a-fA-F]{40}", head_sha) is None:
            reason = "Head SHA must contain exactly 40 hexadecimal characters."
        base_claim = {
            "id": claim_id,
            "bounty_id": bounty_id,
            "hunter": claimant,
            "head_sha": head_sha.lower() if isinstance(head_sha, str) else "",
            "bond_wei": str(value),
            "created_at": now(),
            "status": "REFUNDABLE_ERROR_PENDING" if reason else "IDENTITY_CHECK_PENDING",
            "bond_status": "REFUND_PENDING" if reason else "HELD",
            "reason": reason,
            "next_criterion": 0,
            "judging_criterion_index": -1,
            "verdicts": [],
        }
        self._put_claim(base_claim)
        self._append_claim(bounty_id, claim_id)
        if reason:
            if value > 0:
                gl.get_contract_at(gl.message.contract_address).emit(on="finalized").refund_invalid_claim(claim_id)
            return claim_id
        def identity_check():
            return matches_identity_trailer(
                bounty["repo"], bounty["base_sha"], head_sha.lower(), claimant
            )

        identity = gl.eq_principle.strict_eq(identity_check)
        base_claim = self._get_claim(claim_id)
        if identity.get("status") != 200:
            base_claim["status"] = "IDENTITY_INSUFFICIENT_PENDING"
            base_claim["bond_status"] = "REFUND_PENDING"
            base_claim["reason"] = "GitHub claimant trailer could not be verified; bond will be returned."
        elif identity.get("match"):
            base_claim["status"] = "PENDING"
            base_claim["identity_status"] = "MATCH"
            base_claim["reason"] = "Claimant trailer matches the sending address."
        else:
            base_claim["status"] = "IDENTITY_MISMATCH_PENDING"
            base_claim["bond_status"] = "FORFEIT_PENDING"
            base_claim["identity_status"] = "MISMATCH"
            base_claim["reason"] = "Pinned commit patch does not contain this hunter's Bounty-Claimant trailer."
        self._put_claim(base_claim)
        if base_claim["status"] in ("IDENTITY_INSUFFICIENT_PENDING", "IDENTITY_MISMATCH_PENDING"):
            gl.get_contract_at(gl.message.contract_address).emit(on="finalized").settle_identity(claim_id)
        return claim_id

    @gl.public.write
    def refund_invalid_claim(self, claim_id: str) -> None:
        self._self_only()
        claim = self._get_claim(claim_id)
        if claim.get("status") != "REFUNDABLE_ERROR_PENDING":
            return
        amount = int(claim.get("bond_wei", "0"))
        claim["status"] = "REFUNDABLE_ERROR"
        claim["bond_status"] = "REFUNDED"
        self._put_claim(claim)
        if amount:
            Recipient(Address(claim["hunter"])).emit_transfer(value=u256(amount), on="finalized")

    @gl.public.write
    def settle_identity(self, claim_id: str) -> None:
        self._self_only()
        claim = self._get_claim(claim_id)
        bounty = self._get_bounty(claim.get("bounty_id", ""))
        amount = int(claim.get("bond_wei", "0"))
        if claim.get("status") == "IDENTITY_MISMATCH_PENDING":
            claim["status"] = "IDENTITY_MISMATCH"
            claim["bond_status"] = "FORFEITED"
            if bounty:
                bounty["forfeited_bonds_wei"] = str(int(bounty.get("forfeited_bonds_wei", "0")) + amount)
                self._put_bounty(bounty)
            self._put_claim(claim)
            if amount:
                Recipient(Address(bounty["funder"])).emit_transfer(value=u256(amount), on="finalized")
        elif claim.get("status") == "IDENTITY_INSUFFICIENT_PENDING":
            claim["status"] = "INSUFFICIENT_EVIDENCE"
            claim["bond_status"] = "REFUNDED"
            self._put_claim(claim)
            if amount:
                Recipient(Address(claim["hunter"])).emit_transfer(value=u256(amount), on="finalized")

    @gl.public.write
    def judge_next(self, bounty_id: str) -> str:
        bounty = self._get_bounty(bounty_id)
        require(bounty.get("status") in ("OPEN", "WINNER_REFUNDS_PENDING"), "open bounty required")
        require(now() < int(bounty.get("deadline", 0)) + GRACE_SECONDS, "deadline grace elapsed; close the bounty")
        if bounty.get("status") == "WINNER_REFUNDS_PENDING":
            self.refund_pending(bounty_id)
            return "REFUNDS_SWEPT"
        ids = self._claim_ids(bounty_id)
        for claim_id in ids:
            claim = self._get_claim(claim_id)
            if claim.get("status") == "JUDGING":
                raise gl.vm.UserError("[EXPECTED] An earlier criterion is still being judged.")
            if claim.get("status") != "PENDING":
                continue
            index = int(claim.get("next_criterion", 0))
            if index >= len(bounty.get("criteria", [])):
                continue
            claim["status"] = "JUDGING"
            claim["judging_criterion_index"] = index
            self._put_claim(claim)
            meta = bounty.get("criterion_specs", [])[index]
            gl.get_contract_at(self.patch_judge).emit(on="finalized").judge(
                bounty_id,
                claim_id,
                bounty["repo"],
                bounty["base_sha"],
                claim["head_sha"],
                index,
                bounty["criteria"][index],
                json.dumps(meta, sort_keys=True),
            )
            return claim_id
        raise gl.vm.UserError("[EXPECTED] No pending claim is ready for judgment.")

    @gl.public.write
    def complete_judgment(self, bounty_id: str, claim_id: str, criterion_index: int, result_json: str) -> None:
        require(lower_address(gl.message.sender_address) == lower_address(self.patch_judge), "PatchJudge only")
        bounty = self._get_bounty(bounty_id)
        claim = self._get_claim(claim_id)
        if bounty.get("status") in ("CLOSING", "CLOSED", "REWARD_REFUND_PENDING", "WINNER_REFUNDS_PENDING"):
            return
        if claim.get("status") != "JUDGING" or int(claim.get("judging_criterion_index", -1)) != int(criterion_index):
            return
        result = json.loads(result_json)
        verdict = result.get("verdict")
        if verdict not in ("MET", "NOT_MET", "INSUFFICIENT_EVIDENCE"):
            verdict = "INSUFFICIENT_EVIDENCE"
            result = {"verdict": verdict, "quote": "", "reason": "Invalid validator result; the bond is returned.", "digest": "", "evidence_class": "LLM_ERROR"}
        verdict_record = {
            "criterion_index": int(criterion_index),
            "criterion": bounty["criteria"][int(criterion_index)],
            "verdict": verdict,
            "quote": result.get("quote", ""),
            "reason": str(result.get("reason", ""))[:200],
            "digest": result.get("digest", ""),
            "evidence_class": result.get("evidence_class", "OK"),
            "recorded_at": now(),
        }
        claim.setdefault("verdicts", []).append(verdict_record)
        claim["judging_criterion_index"] = -1
        if verdict == "MET":
            claim["next_criterion"] = int(criterion_index) + 1
            if claim["next_criterion"] == len(bounty["criteria"]):
                claim["status"] = "WIN_PENDING"
                bounty["status"] = "AWARD_PENDING"
                bounty["winner_id"] = claim_id
                gl.get_contract_at(gl.message.contract_address).emit(on="finalized").settle_winner(bounty_id, claim_id)
            else:
                claim["status"] = "PENDING"
        elif verdict == "NOT_MET":
            claim["status"] = "FAIL_PENDING"
            gl.get_contract_at(gl.message.contract_address).emit(on="finalized").settle_failed(claim_id)
        else:
            claim["status"] = "INSUFFICIENT_PENDING"
            gl.get_contract_at(gl.message.contract_address).emit(on="finalized").settle_insufficient(claim_id)
        self._put_claim(claim)
        self._put_bounty(bounty)

    @gl.public.write
    def settle_failed(self, claim_id: str) -> None:
        self._self_only()
        claim = self._get_claim(claim_id)
        if claim.get("status") != "FAIL_PENDING":
            return
        bounty = self._get_bounty(claim["bounty_id"])
        amount = int(claim.get("bond_wei", "0"))
        claim["status"] = "FAILED"
        claim["bond_status"] = "FORFEITED"
        bounty["forfeited_bonds_wei"] = str(int(bounty.get("forfeited_bonds_wei", "0")) + amount)
        self._put_claim(claim)
        self._put_bounty(bounty)
        if amount:
            Recipient(Address(bounty["funder"])).emit_transfer(value=u256(amount), on="finalized")

    @gl.public.write
    def settle_insufficient(self, claim_id: str) -> None:
        self._self_only()
        claim = self._get_claim(claim_id)
        if claim.get("status") != "INSUFFICIENT_PENDING":
            return
        amount = int(claim.get("bond_wei", "0"))
        claim["status"] = "INSUFFICIENT_EVIDENCE"
        claim["bond_status"] = "REFUNDED"
        self._put_claim(claim)
        if amount:
            Recipient(Address(claim["hunter"])).emit_transfer(value=u256(amount), on="finalized")

    def _refund_winner_batch(self, bounty):
        bounty_id = bounty["id"]
        ids = self._claim_ids(bounty_id)
        start = int(bounty.get("refund_cursor", 0))
        end = min(start + SETTLE_BATCH, len(ids))
        winner_id = bounty.get("winner_id", "")
        for index in range(start, end):
            claim_id = ids[index]
            if claim_id == winner_id:
                continue
            claim = self._get_claim(claim_id)
            if claim.get("status") in ("PENDING", "JUDGING", "IDENTITY_CHECK_PENDING") and claim.get("bond_status") == "HELD":
                amount = int(claim.get("bond_wei", "0"))
                claim["status"] = "REFUNDED_AFTER_WIN"
                claim["bond_status"] = "REFUNDED"
                self._put_claim(claim)
                if amount:
                    Recipient(Address(claim["hunter"])).emit_transfer(value=u256(amount), on="finalized")
        bounty["refund_cursor"] = end
        bounty["status"] = "CLOSED" if end >= len(ids) else "WINNER_REFUNDS_PENDING"
        self._put_bounty(bounty)

    @gl.public.write
    def settle_winner(self, bounty_id: str, claim_id: str) -> None:
        self._self_only()
        bounty = self._get_bounty(bounty_id)
        claim = self._get_claim(claim_id)
        if bounty.get("status") != "AWARD_PENDING" or claim.get("status") != "WIN_PENDING":
            return
        reward = int(bounty.get("reward_remaining_wei", "0"))
        bond = int(claim.get("bond_wei", "0"))
        bounty["reward_remaining_wei"] = "0"
        bounty["winner_id"] = claim_id
        bounty["closed_at"] = now()
        claim["status"] = "WON"
        claim["bond_status"] = "PAID"
        self._put_claim(claim)
        if reward + bond:
            Recipient(Address(claim["hunter"])).emit_transfer(value=u256(reward + bond), on="finalized")
        self._refund_winner_batch(bounty)

    @gl.public.write
    def refund_pending(self, bounty_id: str) -> None:
        bounty = self._get_bounty(bounty_id)
        require(bounty.get("status") == "WINNER_REFUNDS_PENDING", "winner refunds are not pending")
        self._refund_winner_batch(bounty)

    @gl.public.write
    def close(self, bounty_id: str) -> None:
        bounty = self._get_bounty(bounty_id)
        require(now() >= int(bounty.get("deadline", 0)) + GRACE_SECONDS, "deadline grace has not elapsed")
        require(bounty.get("status") in ("OPEN", "CLOSING"), "open or closing bounty required")
        bounty["status"] = "CLOSING"
        ids = self._claim_ids(bounty_id)
        start = int(bounty.get("close_cursor", 0))
        end = min(start + SETTLE_BATCH, len(ids))
        for index in range(start, end):
            claim = self._get_claim(ids[index])
            if claim.get("status") in ("PENDING", "JUDGING", "IDENTITY_CHECK_PENDING") and claim.get("bond_status") == "HELD":
                criterion_index = int(claim.get("next_criterion", 0))
                if criterion_index < len(bounty.get("criteria", [])):
                    claim.setdefault("verdicts", []).append({
                        "criterion_index": criterion_index,
                        "criterion": bounty["criteria"][criterion_index],
                        "verdict": "INSUFFICIENT_EVIDENCE",
                        "quote": "",
                        "reason": "Deadline plus 30-minute grace elapsed; unjudged criterion is insufficient evidence.",
                        "digest": "",
                        "evidence_class": "DEADLINE_FALLBACK",
                        "recorded_at": now(),
                    })
                amount = int(claim.get("bond_wei", "0"))
                claim["status"] = "INSUFFICIENT_EVIDENCE"
                claim["bond_status"] = "REFUNDED"
                claim["reason"] = "Deadline fallback returned the pending claim bond."
                self._put_claim(claim)
                if amount:
                    Recipient(Address(claim["hunter"])).emit_transfer(value=u256(amount), on="finalized")
        bounty["close_cursor"] = end
        if end >= len(ids):
            bounty["status"] = "REWARD_REFUND_PENDING"
            self._put_bounty(bounty)
            gl.get_contract_at(gl.message.contract_address).emit(on="finalized").refund_close_reward(bounty_id)
        else:
            self._put_bounty(bounty)

    @gl.public.write
    def refund_close_reward(self, bounty_id: str) -> None:
        self._self_only()
        bounty = self._get_bounty(bounty_id)
        if bounty.get("status") != "REWARD_REFUND_PENDING":
            return
        amount = int(bounty.get("reward_remaining_wei", "0"))
        bounty["reward_remaining_wei"] = "0"
        bounty["status"] = "CLOSED"
        bounty["closed_at"] = now()
        self._put_bounty(bounty)
        if amount:
            Recipient(Address(bounty["funder"])).emit_transfer(value=u256(amount), on="finalized")

    @gl.public.write
    def record_transaction(self, bounty_id: str, action: str, tx_hash: str) -> None:
        require(re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash) is not None, "transaction hash required")
        require(2 <= len(action) <= 120 and action.startswith(("board:", "judge:")), "board or judge action key required")
        bounty = self._get_bounty(bounty_id)
        require(bool(bounty), "known bounty required")
        storage_key = bounty_id + ":" + action
        existing = self.transaction_hashes.get(storage_key, "")
        require(not existing or existing.lower() == tx_hash.lower(), "action hash is already pinned")
        expected_to = lower_address(self.patch_judge) if action.startswith("judge:") else lower_address(gl.message.contract_address)

        def verify():
            item = rpc_transaction(tx_hash)
            return {"valid": item["valid"] and item["to"] == expected_to, "to": item["to"], "status": item["status"]}

        try:
            verified = gl.eq_principle.strict_eq(verify)
        except Exception:
            verified = {"valid": False}
        require(verified.get("valid") is True, "finalized transaction to the expected contract required")
        if existing:
            return
        self.transaction_hashes[storage_key] = tx_hash.lower()
        items = json.loads(self.transaction_lists.get(bounty_id, "[]"))
        items.append({"action": action, "hash": tx_hash.lower()})
        self.transaction_lists[bounty_id] = json.dumps(items, sort_keys=True)
        bounty["transactions"] = items
        self._put_bounty(bounty)

    @gl.public.view
    def get_bounty(self, bounty_id: str) -> dict:
        return self._get_bounty(bounty_id)

    @gl.public.view
    def get_bounty_ids(self, offset: int, limit: int) -> list[str]:
        require(0 <= offset and 1 <= limit <= 50, "pagination bounds")
        return list(self.bounty_ids[offset:offset + limit])

    @gl.public.view
    def get_claims(self, bounty_id: str, offset: int, limit: int) -> list[dict]:
        require(0 <= offset and 1 <= limit <= 50, "pagination bounds")
        ids = self._claim_ids(bounty_id)
        return [self._get_claim(claim_id) for claim_id in ids[offset:offset + limit]]

    @gl.public.view
    def get_verdicts(self, bounty_id: str, offset: int, limit: int) -> list[dict]:
        require(0 <= offset and 1 <= limit <= 50, "pagination bounds")
        claims = self._claim_ids(bounty_id)
        result = []
        for claim_id in claims[offset:offset + limit]:
            record = self._get_claim(claim_id)
            for verdict in record.get("verdicts", []):
                result.append({"claim_id": claim_id, **verdict})
        return result

    @gl.public.view
    def get_balances(self, bounty_id: str) -> dict:
        bounty = self._get_bounty(bounty_id)
        held_bonds = 0
        for claim_id in self._claim_ids(bounty_id):
            claim = self._get_claim(claim_id)
            if claim.get("bond_status") in ("HELD", "REFUND_PENDING", "FORFEIT_PENDING"):
                held_bonds += int(claim.get("bond_wei", "0"))
        return {
            "contract_balance_wei": str(int(self.balance)),
            "reward_remaining_wei": bounty.get("reward_remaining_wei", "0"),
            "claim_bonds_held_wei": str(held_bonds),
            "forfeited_bonds_wei": bounty.get("forfeited_bonds_wei", "0"),
            "winner_id": bounty.get("winner_id", ""),
        }

    @gl.public.view
    def get_transaction_hashes(self, bounty_id: str) -> list[dict]:
        return json.loads(self.transaction_lists.get(bounty_id, "[]"))

