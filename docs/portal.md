# GenLayer Portal submission fields

**Status:** prepared for the owner. This document is not a submitted form.

## Contribution type

Projects

## One-line pitch

Code bounties that pay on the diff, not on the maintainer’s mood.

## Description

Bounty Bench pays code bounties on the diff, not on a maintainer's mood. Paste a GitHub issue and the IssueScout contract drafts acceptance criteria that validators check in code. A funder escrows GEN; hunters submit a pinned commit with a claimant trailer and a bond. GenLayer validators fetch the diff and judge one criterion per transaction, and the Board contract moves money only after finalized verdicts: first passing claim wins, failed claims forfeit bonds, the rest are refunded. Vague specs are rejected with a refund, stuck bounties can always be closed from the app, and three live bounties on real bugs are open to claim now. A Hunt guide walks a reviewer from faucet to claim and checks their commit in the browser first.

## Reviewer steps

1. Open the production app; three live bounties (`bounty-8` to `bounty-10`) are open on real bugs.
2. Open **Scout an issue** and read the IssueScout drafts, including one vague issue rejected as UNACTIONABLE.
3. Open the main bounty (`bounty-3`) and inspect the A–E claim queue, per-criterion verdicts, quotes, digests and bond outcomes.
4. Open `bounty-4`, `bounty-6` and `bounty-7` to see the refund controls and their finalized results.
5. Follow the Hunt guide on an open bounty to claim it yourself.
6. Verify the three contract evidence entries below on StudioNet (chain 61999).

## Expected outcome

The main bounty settles to Hunter D after A fails the claimant-trailer check, B fails the regression-test criterion and C fails the behavior criterion. The rejected spec is refunded, the closing case moves CLOSING to CLOSED across two calls with 21 of 21 refunded, and the winner case pays one claim and refunds 21 across a second step. IssueScout drafts three bounties and rejects one vague issue.

## Evidence entries

Select **GenLayer Explorer Contract** for every contract row.

| Evidence type | Label | URL |
|---|---|---|
| GenLayer Explorer Contract | BountyBoard v3 — StudioNet | https://explorer-studio.genlayer.com/address/0x076C7cd3a79b8991Ce3Bc3B005214d13A1e5E4D5 |
| GenLayer Explorer Contract | PatchJudge v3 — StudioNet | https://explorer-studio.genlayer.com/address/0x739D4947Ecfa7622A79aeBBb91FFA57Ca9dFB898 |
| GenLayer Explorer Contract | IssueScout — StudioNet | https://explorer-studio.genlayer.com/address/0x613D07c39f4a09e5a657A5B6820238cFd7589a53 |
| Website | Bounty Bench production app | https://bounty-bench.vercel.app |
| GitHub repository | Bounty Bench app and contracts | https://github.com/JWattjr/bounty-bench |
| GitHub repository | Public hunter fixture library | https://github.com/JWattjr/bounty-bench-fixtures |

Logo: `public/logo.png`. Demo video: `docs/demo/bounty-bench-demo.mp4` (upload to YouTube or X for the Demo URL field).

## Limits

GitHub availability is part of the evidence path, and diffs above 30 KB resolve as insufficient evidence. The claimant trailer is not proof of GitHub account ownership. The model returns only a criterion verdict; code owns the queue, amounts and transfers.
