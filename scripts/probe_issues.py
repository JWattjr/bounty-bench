"""Deploy and run the GitHub issue access probe (v3)."""

import hashlib

from chain import ROOT, load_proof, read, save_proof, tx

proof = load_proof()
source = (ROOT / "contracts/access_probe_v3.py").read_text(encoding="utf-8")
sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
if "AccessProbeV3" not in proof["contracts"]:
    receipt = tx(proof, "probe-v3-deploy", code=source, index=0)
    address = receipt.get("recipient", receipt.get("to_address"))
    if not address:
        raise RuntimeError("Probe deploy finalized without a contract address")
    proof["contracts"]["AccessProbeV3"] = {"address": address, "source": "access_probe_v3.py", "sha256": sha}
    save_proof(proof)
address = proof["contracts"]["AccessProbeV3"]["address"]
tx(proof, "probe-github-issues", address=address, method="run", args=[], index=0)
result = read(address, "get_results")
proof.setdefault("probeResultsIssues", result)
save_proof(proof)
print("ISSUE PROBE", result, flush=True)
