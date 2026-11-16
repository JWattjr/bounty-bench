"""Deploy and resume the mandatory StudioNet GitHub access probe."""

import hashlib

from chain import ROOT, load_proof, read, save_proof, tx


proof = load_proof()
source = (ROOT / "contracts/access_probe_v2.py").read_text(encoding="utf-8")
source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()

if "AccessProbeV2" not in proof["contracts"]:
    receipt = tx(proof, "probe-v2-deploy", code=source, index=0)
    address = receipt.get("recipient", receipt.get("to_address"))
    if not address:
        raise RuntimeError("Probe deploy finalized without a contract address")
    proof["contracts"]["AccessProbeV2"] = {
        "address": address,
        "source": "access_probe_v2.py",
        "sha256": source_sha,
    }
    save_proof(proof)
elif proof["contracts"]["AccessProbeV2"]["sha256"] != source_sha:
    raise RuntimeError("Probe source changed after deployment; use a new probe release")

address = proof["contracts"]["AccessProbeV2"]["address"]
tx(proof, "probe-github-v2", address=address, method="run", args=[], index=0)
proof["probeResults"] = read(address, "get_results")
save_proof(proof)
print("Probe observations saved to deploy/proof.json", flush=True)

