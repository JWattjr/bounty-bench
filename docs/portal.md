# GenLayer Portal submission fields

**Status:** prepared for the owner. This document is not a submitted form.

## Contribution type

Projects

## One-line pitch

Code bounties that pay on the diff, not on the maintainer’s mood.

## Description

Bounty Bench is an open code-bounty board built with two GenLayer Intelligent Contracts and a deployed Next.js app. A funder escrows GEN against a GitHub repository, a pinned base commit, and up to four written acceptance criteria. Hunters submit commits with a claimant trailer and an exact bond. GenLayer validators fetch the pinned diff and judge one criterion at a time. The Board contract enforces queue order and moves funds only after finalized results: a passing first claim receives the reward and its bond, failed claims forfeit their bonds, and other pending bonds are returned. Vague specifications are rejected with reasons and a refund path. If evidence is unavailable or the deadline grace period expires, the contract refunds rather than leaving funds stuck. The live demo covers spec rejection, front-running protection, partial fixes, prompt-injection resistance, a winning fix, and timeout closure.

## Reviewer steps

1. Open the production app and select the main bounty.
2. Compare the frozen criteria and queue with the current BountyBoard reads.
3. Open each claim to inspect the criterion verdicts, evidence quote, digest, bond disposition, and transaction links.
4. Compare Hunter D’s pinned commit diff with the recorded quotes, then inspect the finalized payout and Hunter E’s refund.
5. Open the rejected-spec and timeout cases to confirm their refund outcomes.
6. Use the Explorer contract evidence entries below to verify each deployed address on StudioNet (chain 61999). The app and repository links are additional evidence.

## Expected outcome

The final v3 main bounty settles to Hunter D after A fails the deterministic claimant-trailer check, B fails the required regression-test criterion, and C fails the behavior criterion despite containing an instruction-like comment. Hunter E’s pending bond is refunded. The rejected vague-spec bounty is refunded to the funder, and the 20 wei no-claim timeout bounty has closed after its deadline plus 30-minute grace period and returned its reward. The v3 payouts and cross-contract callbacks are finalized on StudioNet. Earlier v1/v2 attempts are archived separately; v1 includes one explicitly recorded canceled PatchJudge child after `NO_MAJORITY`, and v2 records the LLM insufficient-evidence fallback. Their main bounties remain closeable after the recorded deadlines plus grace, using `python scripts/release.py close-legacy`.

## Evidence entries

Add each deployed contract address as a separate evidence item. Select **GenLayer Explorer Contract** for every contract row. Do not replace any contract address link with a transaction, repository, or app link.

| Evidence type | Label | URL |
|---|---|---|
| GenLayer Explorer Contract | BountyBoard v3 — StudioNet | https://explorer-studio.genlayer.com/address/0x076C7cd3a79b8991Ce3Bc3B005214d13A1e5E4D5 |
| GenLayer Explorer Contract | PatchJudge v3 — StudioNet | https://explorer-studio.genlayer.com/address/0x739D4947Ecfa7622A79aeBBb91FFA57Ca9dFB898 |
| GenLayer Explorer Contract | BountyBoard v2 — StudioNet | https://explorer-studio.genlayer.com/address/0xE5be47C64db6ec6A0dd1EF055F47F31FfAC96930 |
| GenLayer Explorer Contract | PatchJudge v2 — StudioNet | https://explorer-studio.genlayer.com/address/0x290e65B2533DC5da2CeC5f3c81428dBaA4051AAF |
| GenLayer Explorer Contract | BountyBoard v1 — StudioNet | https://explorer-studio.genlayer.com/address/0x2A8a659fEF6E59Bca72BB8e73680AcBA119FFE83 |
| GenLayer Explorer Contract | PatchJudge v1 — StudioNet | https://explorer-studio.genlayer.com/address/0xF180Fc0c5bCBCFE94C18707bA56764D0fC0cbd62 |
| GenLayer Explorer Contract | AccessProbe — StudioNet | https://explorer-studio.genlayer.com/address/0xC18085B2a08eC2d1d73238da3A5E53211E60f79a |
| GenLayer Explorer Contract | AccessProbeV2 — StudioNet | https://explorer-studio.genlayer.com/address/0x6B149DCfBe20c20e411758e6eE7F49372b2e3fa0 |
| Website | Bounty Bench production app | https://bounty-bench.vercel.app |
| GitHub repository | Bounty Bench app and contracts | https://github.com/JWattjr/bounty-bench |
| GitHub repository | Public hunter fixture library | https://github.com/JWattjr/bounty-bench-fixtures |

## Honest limitations

GitHub availability is part of the evidence path, and diffs larger than the 30 KB extracted-evidence cap resolve as insufficient evidence. The claimant trailer makes copying another hunter’s public commit harder but does not establish legal identity or GitHub account ownership. The language model returns only a criterion verdict; code owns the queue, amounts, and transfers. StudioNet and its Explorer are the demo network and record source.
