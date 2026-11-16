# StudioNet GitHub access probe

The required probe was deployed before the main bounty contract. Both probe contracts use the pinned runner from the build prompt. StudioNet validators reached the pinned `github.com` compare endpoints with a browser user agent.

## Finalized probe transactions

- `AccessProbe` deployed at [`0xC18085B2a08eC2d1d73238da3A5E53211E60f79a`](https://explorer-studio.genlayer.com/address/0xC18085B2a08eC2d1d73238da3A5E53211E60f79a). Its deployment finalized successfully. The first strict-digest run, [`0x34ea4791e28bacc7cbd6e67f95b3ac4471881d45789ef40eae309dc0e2b161f2`](https://explorer-studio.genlayer.com/tx/0x34ea4791e28bacc7cbd6e67f95b3ac4471881d45789ef40eae309dc0e2b161f2), finalized with `MAJORITY_DISAGREE`: the pinned large `.patch` response did not have a validator-stable digest.
- `AccessProbeV2` deployed at [`0x6B149DCfBe20c20e411758e6eE7F49372b2e3fa0`](https://explorer-studio.genlayer.com/address/0x6B149DCfBe20c20e411758e6eE7F49372b2e3fa0). The retry, [`0x6697dec200f90cd7cbbc2e2c598ce3c15c4ed953721a34aa7fc21d4572229caf`](https://explorer-studio.genlayer.com/tx/0x6697dec200f90cd7cbbc2e2c598ce3c15c4ed953721a34aa7fc21d4572229caf), finalized successfully. Each validator re-fetched all four URLs and agreed on HTTP status and the 30 KB / 2 MB size class. The transaction stored the leader's exact byte count and SHA-256 for each response; those digests are recorded in `deploy/proof.json`.

The successful probe deliberately compares status and size class, rather than claiming the very large response bytes are identical. The production `PatchJudge` applies the stricter rule required for bounty evidence: it refetches the selected diff, checks the extracted digest, and requires the judge's verbatim quote to occur in each validator's own extract.

## Measured responses

| Public compare | Format | HTTP | GenVM response bytes | SHA-256 | Effect |
|---|---:|---:|---:|---|---|
| `octocat/Hello-World`, `553c207…` → `7fd1a60…` | `.diff` | 200 | 157 | `b9f0e648c3b11a522fc2db0348b3814ccdec3d5a8e4a70a8a458cd2cd6c7897f` | Small pinned diff, usable |
| `octocat/Hello-World`, `553c207…` → `7fd1a60…` | `.patch` | 200 | 464 | `f7bfb71f679b84c3c00dc4c4bac4902480afa862b453b738e0816bbb2e87c485` | Small pinned patch, usable for the deterministic claimant-trailer check |
| `torvalds/linux`, `0c38364…` → `98f7e32…` | `.diff` | 200 | 83,584,504 | `e05e7f3ad152e48bb53852212447453d8d32bbca2e03df9a270fb76561e11185` | Over 2 MB and 30 KB; judge returns `INSUFFICIENT_EVIDENCE` |
| `torvalds/linux`, `0c38364…` → `98f7e32…` | `.patch` | 200 | 135,280 | `ed5efd07d7eb2ca6a20528c5229be15fd4ede86cd9c03987df483e5cffe7f73e` | Over 30 KB; judge returns `INSUFFICIENT_EVIDENCE` |

Full 40-character SHAs and URLs are embedded in both probe sources. For the Linux range, an HTTP `HEAD` outside the validator showed a 12,310,930-byte compressed response length; GenVM counted the decompressed body at 83,584,504 bytes.

## Source decision

`github.com` was reachable, so no alternate host was needed. The app uses the small `.patch` endpoint only for the deterministic trailer check and the `.diff` endpoint for criterion judgment. Any extracted evidence over 30,000 bytes, any fetch failure, or a digest mismatch becomes `INSUFFICIENT_EVIDENCE`; the claim bond is returned. This avoids sending a giant patch to the model or treating a large external response as hunter fault.

