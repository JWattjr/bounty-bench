# Build decisions

These choices follow the attached, pre-approved build prompt. No owner questions or signature handoffs are part of the build.

## Product and visual direction

- Use the Bounty Bench name and the supplied one-line pitch.
- Treat the home screen and case pages as a desktop code-review workbench. Make the bounty queue, pinned diff, criterion state, and settlement trail the main visual material; use monospace for hashes and diff evidence. The exact palette, layout, type pairing, and component character are agent-selected under the prompt's delegated visual decision.
- The surface is an operational product, not a marketing landing page. Prioritize scanability, evidence, and trustworthy states.

## Chain and contract choices

- StudioNet, chain ID 61999, RPC `https://studio.genlayer.com/api`, canonical Explorer `https://explorer-studio.genlayer.com`.
- Use the runner hash and Python/GenLayer SDK versions specified in the build prompt and matching `refund-court/requirements.txt`.
- Probe validator access to pinned GitHub compare `.diff` and `.patch` endpoints before implementing the bounty contract.
- Probe result: small GitHub `.diff` and `.patch` responses were HTTP 200; the pinned Linux `.diff` was 83,584,504 bytes after decompression. Large responses exceed the 30 KB cap and are insufficient evidence. Keep GitHub as the source; see `docs/probe.md`.
- Begin with separate `PatchJudge` and `BountyBoard` contracts. If live cross-contract callbacks fail, use the prompt's approved single-contract fallback and document the observed reason.
- Diff evidence passed to a judge is capped at 30,000 bytes. Oversize and fetch failures become `INSUFFICIENT_EVIDENCE`.
- The fixed demo values are a 15 wei rejected-spec reward, 50 wei main reward, 20 wei timeout reward, and 5 wei per claim bond. The five hunters receive 5 wei each; the first funding pass gave the funder 85 wei and seeded each hunter with 5 wei.
- If transfer auto-review blocks source funding, continue all work not requiring the funds and retry only after recording the supplied authorization evidence in the action justification.

## Visual work record

- The attached prompt delegates the visual direction and identifies a dark code-review feel as a fit. This is treated as the user's authorization to resolve the direction without an approval round.
- The Impeccable direction seed assigned candidate 4, a dated gate-board queue with segmented evidence tickets. The fused challenger `digital-design-canon-dark-first-developer-console` is stronger for both developer-audience identification and explaining the product mechanism, so it is the selected system. The gate-board queue's useful discipline is retained: claim order stays fixed, and verdict state changes in place. The interface will use a dark-first developer workbench with a chronological claim rail, not literal travel graphics.
- The other challengers were declined because they weakened both audience identification and product clarity. Their useful disciplines are raised into this direction: clear typographic scale (variable-font specimen), serial IDs as the navigation spine (catalog sleeve), stable focus on one claim's evidence (vertical feed), and a visible trace between a quote and its diff hunk (star atlas).
- Build path: code-led for a dense operational workbench with no necessary external raster assets. This is a session choice, not a stored Impeccable preference.

## Demo fixture

- Use a tiny Python slug normalization library with a real repeated-hyphen/edge-hyphen bug.
- Hunter B fixes the function without adding a test. Hunter C adds an instruction-like comment but leaves the bug unfixed. Hunter D and Hunter E carry a complete fix and test. Hunter A reuses D's commit under A's address and therefore fails the trailer check.
- The timeout bounty deadline is set at least 65 minutes ahead of the local clock, with the contract's 30-minute grace period. The extra five minutes absorbs local-clock and block-time skew; the initial exact-60-minute payable attempt was refunded by the contract and is retained in proof.

## Signing and evidence

- Generate six dedicated EVM accounts. Their private keys live only in the ignored `bounty-bench/.env`; never print or commit them.
- Record every source funding transfer in `deploy/funding.json`. Record all deploy, case, judge, and settlement transactions in `deploy/proof.json` before polling.
- Keep the Portal fields in `docs/portal.md`; do not submit the Portal form.
- Add each deployed contract's direct Explorer address URL as its own prepared Portal evidence entry with type `GenLayer Explorer Contract`. Verify each link against the StudioNet Explorer API and the RPC.

## Live release hardening

- v1's PatchJudge child for Hunter D's third criterion ended `CANCELED / NO_MAJORITY`. That immutable Board could not reset a stale `JUDGING` claim, so the release was archived and its timeout was closed after grace.
- v2 added stale-judgment retries, but the model returned `LLM_ERROR` for the regression-test criterion. The Board refunded D's bond and left that release's main bounty without a winner; its source, transactions, and eventual cleanup eligibility are preserved.
- v3 keeps the ordered Board/Judge design and checks this narrow test criterion against an added assertion: the named function is called with repeated hyphens and the expected value contains one hyphen. Other criterion shapes still use the validator LLM. A direct-mode regression test covers this path.
- The v3 live case finalized the three criteria, paid Hunter D, returned Hunter E's bond, settled the rejected-spec case, and closed/refunded the 20 wei no-claim timeout after the 30-minute grace period.
- Seed transfers total 265 wei across the original run and replays. Planned gross seed, reward, bond, and payout movements total 965 wei, inside the 1,000 wei authorization; see `deploy/funding.json`.

