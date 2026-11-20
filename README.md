# Bounty Bench

Code bounties that pay on the diff, not on the maintainer’s mood.

Paste a GitHub issue and IssueScout turns it into acceptance criteria that a code diff can prove. Fund it, and hunters submit a pinned commit with a claimant trailer. GenLayer validators fetch the diff and judge one criterion per transaction. The Board contract orders claims and moves rewards and bonds only after finalized code decisions, so nobody has to trust a maintainer to pay.

## Try it in two minutes

1. Open [bounty-bench.vercel.app](https://bounty-bench.vercel.app). Three live bounties on real bugs are open for claims (`bounty-8`, `bounty-9`, `bounty-10`).
2. Open one and follow the **Hunt guide**: fund a wallet from the StudioNet faucet button, fork the fixture repo, commit a fix with the `Bounty-Claimant:` trailer, then paste the head SHA. The page checks the base commit and trailer in your browser before you spend a bond.
3. Or open **Scout an issue**, paste a public issue URL, and review the drafted criteria before posting them as a bounty.

## Network deployment

- Network: GenLayer StudioNet, chain ID `61999`.
- Current BountyBoard: [`0x076C7cd3a79b8991Ce3Bc3B005214d13A1e5E4D5`](https://explorer-studio.genlayer.com/address/0x076C7cd3a79b8991Ce3Bc3B005214d13A1e5E4D5)
- Current PatchJudge: [`0x739D4947Ecfa7622A79aeBBb91FFA57Ca9dFB898`](https://explorer-studio.genlayer.com/address/0x739D4947Ecfa7622A79aeBBb91FFA57Ca9dFB898)
- Public fixture repository: [JWattjr/bounty-bench-fixtures](https://github.com/JWattjr/bounty-bench-fixtures)
- Current IssueScout: [`0x613D07c39f4a09e5a657A5B6820238cFd7589a53`](https://explorer-studio.genlayer.com/address/0x613D07c39f4a09e5a657A5B6820238cFd7589a53)
- Live app: [bounty-bench.vercel.app](https://bounty-bench.vercel.app); the final deployment URL is also recorded in [`deploy/proof.json`](deploy/proof.json).

## Scout an issue

`IssueScout` drafts bounty criteria from a public GitHub issue. The leader fetches the issue and proposes one to four criteria; validators re-fetch it, require the same issue digest, and check the draft in code: allowed shapes, unique 20–300 character criteria, one behavior criterion, and every backticked identifier must appear in the issue text. Vague issues return `UNACTIONABLE`. Live drafts: three drafted from the fixture bugs (`draft-1` to `draft-3`) and one rejected as vague (`draft-4`). The GitHub issue API was confirmed reachable by validators with a third probe contract before this was built.

## Live open bounties

`bounty-8`, `bounty-9` and `bounty-10` were created through the app’s own write path from the IssueScout drafts, each with a three-week deadline, a 10 wei reward and a 1 wei bond. They are open now and can be claimed by anyone.

## Refund controls

The bounty page exposes every settlement step a stuck bounty can need, each proven live through the app’s write path:

| Control | Contract call | Proof |
|---|---|---|
| Refund rejected reward | `refund_rejected` | `bounty-4` SPEC_REJECTED → REJECTED_REFUNDED, [tx](https://explorer-studio.genlayer.com/tx/0xd37fc679f9cf8d1d7a4e9e13dbd7655df0546ef68773b17dd85cd1228ce20c50) |
| Continue closing (repeatable) | `close` | `bounty-7` CLOSING at cursor 20 after the first call, CLOSED with 21 of 21 refunded after the second: [first](https://explorer-studio.genlayer.com/tx/0xe3945fe93002cf1d7a71e234005d61dc9159f29c7dbfe5aec4b163bb450ae10f), [second](https://explorer-studio.genlayer.com/tx/0xdf67e1289619f8af75d8cefd9b6a75f18f9288334f818c01f386f3172de60533) |
| Continue winner refunds | `refund_pending` | `bounty-6` WINNER_REFUNDS_PENDING at cursor 20 → CLOSED, 1 paid and 21 refunded, [tx](https://explorer-studio.genlayer.com/tx/0xf26181f2dc525ff3e78b97e190e02843148ca203fdb422d039e9f80342db3794) |

Source at commit `9abd8f6`: [bounty-detail.tsx L77–79](https://github.com/JWattjr/bounty-bench/blob/9abd8f6/components/bounty-detail.tsx#L77-L79) and [L172–176](https://github.com/JWattjr/bounty-bench/blob/9abd8f6/components/bounty-detail.tsx#L172-L176); contract entrypoints [`refund_rejected` L240](https://github.com/JWattjr/bounty-bench/blob/9abd8f6/contracts/bounty_board.py#L240), [`refund_pending` L556](https://github.com/JWattjr/bounty-bench/blob/9abd8f6/contracts/bounty_board.py#L556), [`close` L562](https://github.com/JWattjr/bounty-bench/blob/9abd8f6/contracts/bounty_board.py#L562). An earlier closing attempt (`bounty-5`) is kept in `deploy/proof.json`.

## Release history

- **v1** — [BountyBoard](https://explorer-studio.genlayer.com/address/0x2A8a659fEF6E59Bca72BB8e73680AcBA119FFE83) · [PatchJudge](https://explorer-studio.genlayer.com/address/0xF180Fc0c5bCBCFE94C18707bA56764D0fC0cbd62). Hunter D’s third-criterion PatchJudge child ended `CANCELED / NO_MAJORITY`; the immutable Board could not reset the stale `JUDGING` claim, so v1 was archived.
- **v2** — [BountyBoard](https://explorer-studio.genlayer.com/address/0xE5be47C64db6ec6A0dd1EF055F47F31FfAC96930) · [PatchJudge](https://explorer-studio.genlayer.com/address/0x290e65B2533DC5da2CeC5f3c81428dBaA4051AAF). The model returned `LLM_ERROR` for the regression-test criterion; the Board refunded D’s bond and left the main bounty without a winner, so v3 replaced this attempt.
- **GitHub access probes** — [AccessProbe](https://explorer-studio.genlayer.com/address/0xC18085B2a08eC2d1d73238da3A5E53211E60f79a) · [AccessProbeV2](https://explorer-studio.genlayer.com/address/0x6B149DCfBe20c20e411758e6eE7F49372b2e3fa0). The large patch did not produce a validator-stable digest, and oversized diffs exceeded 30 KB; v3 retained GitHub but judged bounded extracts with validator-stable quote and digest checks.

`deploy/proof.json` records active and retired contract source hashes, every transaction hash including nested callbacks, and the observed result for each release. `npm run verify:proof` checks each direct StudioNet Explorer address page, contract API record, RPC chain ID, and transaction status. Proof snapshots are labeled separately from current reads in the app. 

## Architecture

```mermaid
flowchart LR
  F[Funder] -->|reward + frozen criteria| B[BountyBoard]
  H[Hunters] -->|ordered claim + bond| B
  B -->|finalized compile request| J[PatchJudge]
  J -->|validator web fetch| GH[GitHub pinned .diff / .patch]
  J -->|one criterion, quote, digest| B
  B -->|finalized payout / refund / forfeit| W[Winner, hunter, or funder]
  V[GenLayer validators] -. re-fetch and verify . .-> GH
  V -. consensus result .-> J
```

`BountyBoard` owns the escrow, frozen criteria, submission-order queue, claimant-trailer check, and deterministic settlement. `PatchJudge` compiles criteria into a constrained observable shape, fetches pinned diffs, extracts bounded evidence, and returns one verdict. It never chooses a winner or an amount. Finalized cross-contract messages connect both contracts; finalized self messages perform money movement.

## Run locally

Requirements: Node.js 24, Python 3.12+, and the exact dependency versions pinned in `package-lock.json` and `requirements.txt`.

```powershell
npm ci
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm run dev
```

The board can be read without a wallet. To write, connect an EIP-1193 wallet with StudioNet selected. The create form takes a reward in wei, a fixed bond, a deadline, the repository and base SHA, and one to four criteria. A claim sends exactly the frozen bond. The judgment and close controls call the deployed Board contract.

## Contract and proof workflow

The current project deploys with the pinned runner hash in each contract header. The funded live-demo keys are kept in the ignored `.env`; never commit that file. The test funding manifest lists the source, destinations, and amounts without private keys.

```powershell
python scripts/lint_contracts.py
python -m pytest tests/direct -q
python scripts/release.py deploy
python scripts/release.py cases
python scripts/release.py timeout
python scripts/release.py close-legacy
npm run typecheck
npm run verify:proof
```

The release script stores each submitted hash before polling and resumes from that hash after interruption. The `cases` stage opens the rejected-spec, timeout, and five-claim competition bounties. The `timeout` stage closes the active timeout after its deadline plus the 30-minute grace period. The `close-legacy` stage closes any eligible archived release cases after their grace periods. Direct-mode tests use mocked GitHub and LLM results; they are regression checks, not evidence that a live case passed.

## Reviewer path

1. Open the production app and choose the main bounty from the queue.
2. Read the frozen criteria hash and inspect the fixed A–E claim order.
3. Select a claim to inspect the per-criterion verdict, exact quote, SHA-256, bond disposition, and transaction Explorer link.
4. Open the linked commit diff and compare it with the displayed quote.
5. Compare those current reads with the recorded run in `deploy/proof.json`.

## Limits

- GitHub must return the pinned compare response to validators. Fetch errors produce `INSUFFICIENT_EVIDENCE` and return the bond.
- The extracted diff is capped at 30,000 bytes. Oversize evidence is insufficient and the bond is refunded.
- The claimant trailer blocks reuse of another hunter’s submitted commit under the demo rule. It is not proof of legal identity or GitHub account ownership.
- Criteria are intentionally narrow. Vague or compound requests are rejected before the reward becomes an open bounty.
- The model judges one criterion; Board code controls ordering, amounts, eligibility, and all transfers. Native GenLayer appeal/finality timing remains authoritative.

## Project files

- `contracts/`: the deployed BountyBoard, PatchJudge, IssueScout, and the GitHub access probes.
- `scripts/`: resumable deployment, proof, funding, fixture, and verification code.
- `deploy/`: public proof and funding manifests; transaction receipts stay in ignored local output.
- `tests/direct/`: direct-mode compiler, claim, verdict, fallback, and payable-refund checks.
- `app/`, `components/`, `lib/`: Next.js interface, public chain reads, transaction state, and EIP-1193 writes.
- `docs/`: implementation decisions, live access probe, tutorial, demo script, and prepared Portal fields.
