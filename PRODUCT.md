# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Next.js on Vercel (remote build), TypeScript client, GenLayer StudioNet intelligent contracts, and Python deployment/demo scripts. The user explicitly selected this stack in the build prompt.

## Users

- **Funders** with a public GitHub repository who want to offer a fixed GEN reward for a code change.
- **Hunters** who can submit a commit to an open bounty and want the acceptance rules and escrow visible before they work.
- **Reviewers** inspecting the live demonstration and its public on-chain evidence.

## Product Purpose

Bounty Bench escrows GEN against a repository, a pinned base commit, and up to four written acceptance criteria. Hunters submit commit SHAs. GenLayer validators independently fetch the pinned diff and judge one criterion at a time. Deterministic contract code pays the first claim that meets every criterion, returns bonds after an evidence failure, and refunds the reward when no claim wins.

Success means a funder can publish an observable code bounty, hunters can submit claims without a wallet-dependent read experience, and anyone can inspect finalized judgments and settlement evidence.

## Positioning

“Code bounties that pay on the diff, not on the maintainer's mood.” The product combines open competition, fixed escrow, spam bonds, pinned GitHub diffs, first-valid-wins ordering, and validator judgment. It differs from a private milestone grant by allowing anonymous hunters to race on one public specification.

## Operating Context

The bounty is created against `owner/repo`, a 40-character base SHA, a title, one to four criteria, a deadline at least 60 minutes in the future, and a fixed claim bond. Each claim provides a head SHA and exact bond. The demo uses a GitHub commit trailer to match each claimant address deterministically. Anyone may judge the next criterion or close an expired bounty after the grace period.

Visitors can inspect the home board and case pages without connecting a wallet. Create, claim, judge, and close actions are available to real wallet users. The prepared live demo is signed by dedicated test accounts and the recorded proof is shown separately from current RPC reads.

## Capabilities and Constraints

- Allowed criteria are tied to observable diff evidence: a named path, a test exercising a named function or behavior, a named function's concrete behavior, or a path boundary.
- Criteria are frozen and hashed before the bounty opens. Vague criteria receive a reason for each rejection.
- Claims follow submission order. The first fully valid claim wins; partial payouts, multiple winners, reputation, ranking, tokens, GitHub OAuth, and a custom appeal court are out of scope.
- GitHub is an external evidence dependency. Diff extracts are capped at approximately 30 KB. A fetch failure or oversized extract is insufficient evidence and returns the hunter's bond.
- Identity uses a `Bounty-Claimant` commit trailer; it is a deterministic check, not proof of legal identity.
- StudioNet is the demo network (chain 61999). Transaction states and GenLayer's appeal window are displayed distinctly.
- The requested demo is desktop-only; no mobile checks are in scope.

## Brand Commitments

The product name and one-line pitch are fixed. The prompt delegates the visual style and says a dark code-review feel with monospace diffs and hashes fits; the implementation will keep diffs, hashes, criteria, and settlement proofs legible as the central product material.

## Evidence on Hand

No Bounty Bench contract or demo outcome was live when this record was written. Public evidence must come from the deployed contracts and finalized demo transactions recorded in `deploy/proof.json`. Never present mocked test results as live proof.

## Product Principles

1. Validators judge evidence; deterministic code controls queue order and money.
2. A pinned diff and frozen criteria make every verdict reviewable.
3. Failed evidence retrieval must not punish the hunter or lock a bounty forever.
4. Reads remain public and useful without a wallet.
5. Recorded proof and live chain reads are labeled separately.

