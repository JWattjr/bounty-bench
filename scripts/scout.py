"""Deploy IssueScout and turn real public fixture issues into drafted criteria (live)."""

import hashlib
import json

from chain import ROOT, load_proof, read, save_proof, tx

REPO = "JWattjr/bounty-bench-fixtures"
ISSUES = [1, 2, 3, 4]  # 1-3 are actionable bugs; 4 is a deliberately vague discussion
proof = load_proof()
source = (ROOT / "contracts/issue_scout.py").read_text(encoding="utf-8")
sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
if "IssueScout" not in proof["contracts"]:
    receipt = tx(proof, "deploy-issue-scout", code=source, index=0)
    address = receipt.get("recipient", receipt.get("to_address"))
    if not address:
        raise RuntimeError("IssueScout deploy finalized without a contract address")
    proof["contracts"]["IssueScout"] = {"address": address, "source": "issue_scout.py", "sha256": sha}
    save_proof(proof)
elif proof["contracts"]["IssueScout"]["sha256"] != sha:
    raise RuntimeError("IssueScout source changed after deployment")
address = proof["contracts"]["IssueScout"]["address"]
scout = proof.setdefault("scout", {"drafts": {}})
for number in ISSUES:
    label = "scout-draft-issue-%d" % number
    tx(proof, label, address=address, method="draft", args=[REPO, number], index=0)
    ids = read(address, "get_draft_ids", [0, 50])
    # the newest draft id belongs to the transaction just finalized
    scout["drafts"].setdefault(str(number), ids[-1])
    record = read(address, "get_draft", [scout["drafts"][str(number)]])
    scout.setdefault("records", {})[str(number)] = record
    save_proof(proof)
    print("DRAFT issue", number, record.get("status"), json.dumps(record.get("criteria")), flush=True)
