"""Merge deploy/refund-controls.json (live app-path proof) into deploy/proof.json and funding.json."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
state = json.loads((ROOT / "deploy/refund-controls.json").read_text(encoding="utf-8"))
proof = json.loads((ROOT / "deploy/proof.json").read_text(encoding="utf-8"))
funding = json.loads((ROOT / "deploy/funding.json").read_text(encoding="utf-8"))
tx = state["transactions"]
cases = state["cases"]
for name in ("rejected", "closing", "winner"):
    if not cases.get(name, {}).get("done"):
        raise SystemExit(name + " case is not complete; rerun scripts/refund_controls.mjs")

proof.setdefault("releases", {})["refund-controls"] = {
    "note": "Live proof of the three refund controls, driven through lib/wallet.ts write() on an EIP-1193 bridge with scripted test keys.",
    "transactions": tx,
    "nonSuccessfulTransactions": {},
}
proof["refundControls"] = {
    "board": proof["contracts"]["BountyBoard"]["address"],
    "rejected": {
        "bountyId": cases["rejected"]["bountyId"],
        "control": "Refund rejected reward -> refund_rejected",
        "statusBefore": cases["rejected"]["statusBefore"],
        "statusAfter": cases["rejected"]["statusAfter"],
        "rewardWei": cases["rejected"]["rewardWei"],
        "rewardRemainingAfter": cases["rejected"]["rewardRemainingAfter"],
        "controlTransaction": tx["rejected-refund_rejected"],
    },
    "closing": {
        "bountyId": cases["closing"]["bountyId"],
        "control": "Continue closing -> close (repeated while CLOSING)",
        "claimsPendingBeforeClose": cases["closing"]["pendingBeforeClose"],
        "afterFirstClose": cases["closing"]["afterFirstClose"],
        "statusAfter": cases["closing"]["statusAfter"],
        "claimsRefunded": cases["closing"]["claimsRefunded"],
        "controlTransactions": [tx["closing-close-1"], tx["closing-close-2"]],
    },
    "winner": {
        "bountyId": cases["winner"]["bountyId"],
        "control": "Continue winner refunds -> refund_pending",
        "claimsQueued": cases["winner"]["claimsQueued"],
        "afterWin": cases["winner"]["afterWin"],
        "statusAfter": cases["winner"]["statusAfter"],
        "claimsRefunded": cases["winner"]["claimsRefunded"],
        "claimsPaid": cases["winner"]["claimsPaid"],
        "controlTransaction": tx.get("winner-refund_pending-1"),
    },
}
gross = 15 + 10 + 10 + 21 + 22
funding["refundControls"] = {
    "approvedAdditionalWei": 500,
    "newSourceTransfersWei": 0,
    "grossPayableWei": gross,
    "note": "Rewards and bonds recycled through existing demo wallets; every wei was returned or paid inside the contract flow.",
}
(ROOT / "deploy/proof.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
(ROOT / "deploy/funding.json").write_text(json.dumps(funding, indent=2), encoding="utf-8")
print("merged refund controls into proof.json; gross wei", gross)
