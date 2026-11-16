# Bounty Bench implementation tutorial

This tutorial follows the contracts and scripts in this repository. It explains how the Board freezes a bounty, how a hunter enters the queue, how PatchJudge checks evidence, and how finalized callbacks settle funds.

## 1. A bounty becomes immutable work

The funder calls `BountyBoard.create_bounty` once with a repository name, a 40-character base SHA, a title, a JSON array of one to four criteria, a deadline, and the fixed claim bond. The transaction value is the reward. The method checks the syntax and deadlines before recording the bounty. If an invalid payable request arrives, the Board records a refundable error and returns the attached reward through a finalized self message; it does not silently hold the value.

For a syntactically valid bounty, the Board stores the canonical criteria JSON and its SHA-256, marks the record `COMPILING`, and emits a finalized `PatchJudge.compile_spec` call. The compiler asks the model for a strict JSON decision for each criterion. A second validator independently runs the same compiler logic. The contract also checks the criterion against four constrained shapes: a concrete path pattern, a named function behavior, a test that exercises a named behavior, or a path boundary. Vague inputs such as “make the code cleaner and well tested” remain rejected even if a model attempts to accept them. `BountyBoard.complete_spec` stores the per-criterion result and only then sets the bounty to `OPEN` or `SPEC_REJECTED`.

The funder can call `refund_rejected` for a rejected bounty. That call changes the record to a pending refund state and schedules `pay_rejected_reward` through `emit(on="finalized")`. The callback is self-only, zeros the recorded remaining reward before emitting the native transfer, and marks the bounty refunded. The tests exercise the recorded state transition; the live proof records the finalized transfer as a nested transaction.

## 2. Claims are ordered and attributable

`BountyBoard.claim` accepts a bounty ID and head SHA with exactly the frozen bond. The method checks that the bounty is open, that the deadline has not passed, that the bond matches, and that the head SHA has the required format. It assigns a claim ID and appends it to `claims_by_bounty`, which is the durable queue order.

The claimant check is deterministic and does not use the model. The Board requests the pinned GitHub `.patch` for the base and head SHAs, then looks for a trailer line matching `Bounty-Claimant: <lowercase sender address>`. A mismatch marks the claim for forfeiture to the funder after finality. A fetch failure becomes `INSUFFICIENT_EVIDENCE` and returns the bond. The trailer is an anti-copy rule for the demo; it does not authenticate a real-world identity.

Invalid payable claims are handled as refundable records. This matters because a hunter may accidentally send the wrong bond or a malformed SHA. Reverting a payable call would leave the wallet to reconcile the failed transaction; recording the intent and refunding the value gives the interface a clear status and keeps accounting visible.

## 3. PatchJudge sees bounded, pinned evidence

Anyone may call `BountyBoard.judge_next`. The Board scans the ordered claim list and selects the oldest claim in `PENDING`, then marks exactly one criterion as `JUDGING`. The emitted `PatchJudge.judge` call receives the frozen repository and SHAs, the criterion text, the criterion index, and the compiler’s constrained metadata.

PatchJudge fetches the compare `.diff` using a browser user agent. It verifies HTTP success and a unified diff, filters by named path patterns when a criterion has one, caps the extracted material at 30,000 bytes, and computes SHA-256 over the evidence it will show the model. Fetch errors, empty evidence, missing matching files, and oversized extracts return `INSUFFICIENT_EVIDENCE` without asking the model to decide. This path protects hunters from being penalized when GitHub is unavailable or a patch is too large to review safely.

For available evidence, the prompt asks for exactly one of `MET`, `NOT_MET`, or `INSUFFICIENT_EVIDENCE`, a verbatim quote, and a short reason. It explicitly treats diff text as untrusted evidence and tells the model to ignore instructions in comments or strings. Each validator re-fetches the diff and re-extracts the excerpt. The `run_nondet_unsafe` validator requires the same digest, the same verdict, and an exact quote contained in that validator’s own excerpt. The model cannot submit a payout amount, reorder the queue, or name a winner.

## 4. Finality controls the money movement

`PatchJudge` stores a compact judgment and emits `BountyBoard.complete_judgment` only after the PatchJudge transaction finalizes. The Board records the criterion, verdict, quote, reason, digest, evidence class, and timestamp. `MET` advances the claim to its next criterion. `NOT_MET` stops that claim and schedules a finalized settlement that forfeits its bond to the funder. `INSUFFICIENT_EVIDENCE` stops that claim and returns the bond. These verdict paths are distinct so that external fetch failures do not look like hunter fault.

When all criteria are `MET`, the Board marks the claim and bounty pending, then emits a self-only `settle_winner` callback after finality. That callback zeros the remaining reward, marks the winner, and transfers reward plus the winner’s bond. It then refunds other held bonds in a bounded batch. `get_balances` exposes the reward, held bonds, forfeitures, and winner so the app can show settlement without an indexer.

The deadline fallback removes unbounded pending claims. After the bounty deadline plus 30 minutes, anyone can call `close`. It marks unjudged claims insufficient, returns their held bonds, and schedules the remaining reward refund to the funder. Long queues can be processed in bounded batches using the stored cursor fields. Each callback checks its current state before paying, so repeating a settled callback is harmless.

## 5. Scripts and interface

`scripts/chain.py` pins `genlayer-py`, loads the ignored signer keys, saves a transaction hash before polling, and recursively records triggered transactions. `scripts/release.py` uses stable operation labels to resume deployments, bounties, claims, and one-criterion judgments. `deploy/proof.json` is the public audit manifest; private keys are never copied into it. `scripts/verify_proof.py` checks the StudioNet chain ID, each contract’s Explorer type and address, source hashes, and finalized transactions through read-only RPC calls.

The Next.js server reads current finalized contract state through `genlayer-js`. The read-only queue works without a wallet. A browser write uses an EIP-1193 provider, switches to StudioNet, and calls `create_bounty`, `claim`, `judge_next`, or `close`. Each submitted hash starts in `SUBMITTED`; the transaction route reads the StudioNet transaction until it becomes pending, accepted, finalized successfully, or finalized with an error. Explorer links use canonical address and transaction paths. The UI labels manifest proof separately from the current RPC snapshot.

The direct-mode tests mock web and model responses to cover compiler rejection, each verdict, injection text, oversize evidence, identity matching, malformed payable claims, and deadline refund behavior. Those tests catch regressions in contract code, but only the live StudioNet transactions in the proof manifest establish the production demo outcomes.
