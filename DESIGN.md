# Bounty Bench design system

## Direction

**Mode:** Operate. **World:** a dark-first developer console for a public code-bounty queue. **Build path:** code-led; the interface itself is the evidence surface, so the contract's criteria, diff quote, digest, queue position, and settlement trail carry the visual weight.

The Impeccable direction seed assigned the gate-board and segmented ticket concept. The dark-first developer-console challenger won on both audience identification and product clarity: funders and hunters recognize a code-review workbench, and its panels can show evidence and settlement without a decorative metaphor. The gate-board contribution survives as a fixed chronological claim rail whose status updates in place.

## First viewport

The page opens on an operational board. A narrow network header identifies StudioNet and the connected wallet state. The left rail gives the product name and the two real destinations (bounties and proof). The main column presents open bounties as a dense, chronologically sortable ledger; a selected bounty opens its acceptance criteria and claim queue. A right proof stack shows the selected case's transaction state, bond/reward movement, and appeal timing. The pitch is present as context, but the live queue demonstrates the mechanism.

## Visitor path

1. Scan open and closed bounties, with reward, deadline, criteria, and queue length visible without a wallet.
2. Open a bounty and check its frozen criteria hash and ordered claims.
3. Select a claim to inspect each verdict, verbatim quote, diff digest, reason, appeal window, and Explorer transaction.
4. Connect a wallet only to create, claim, judge the next criterion, or close an expired bounty.

## Signature interaction

The selected claim stays anchored while each criterion moves through submitted, pending, accepted, finalized-success, or finalized-error. Each finalized verdict adds a compact evidence row and a visible connection to the corresponding diff hunk. The queue order does not change when a row's state changes. The selected claim advances to its next criterion one transaction at a time.

## Materials and tokens

- Graphite background (`#101214`), raised work panels (`#171a1d`), and dividers (`#2b3034`) create a layered workbench without large shadow cards.
- Near-white text is reserved for primary content. Muted steel distinguishes labels and metadata.
- Acid mint marks finalized success and active review. Warm amber marks deadlines, appeal windows, and waiting work. Coral marks rejected criteria and finalized errors.
- Use a compact humanist sans for interface copy and `ui-monospace` for SHAs, diff excerpts, quotes, digests, transaction hashes, and amounts.
- Use tabular numerals for GEN values, timestamps, and queue sequence numbers. Keep claim order as a stable serial spine.

## Component character

- Hairline borders and flat elevations; no glass, gradients, or decorative blur.
- Bounty rows use the same information order: serial, repo and title, reward, deadline, criteria count, claims, status.
- Criteria are labeled by number and their exact frozen text. A verdict is paired with the model's quote, its digest, and the deterministic settlement effect.
- Explorer links always use the canonical address and transaction paths. Recorded proof and live RPC reads have distinct labels.
- Empty, pending, unavailable, rejected, refunded, and closed states remain explicit; no missing data is disguised as a success state.

## Cross-surface behavior

The same hierarchy applies to the home ledger and case page: status and order first, evidence second, action third. On narrow viewports, preserve the claim's identity and status before hiding secondary proof columns. Desktop is the required review target for this release; no mobile check is requested.

## Honest risk

GitHub availability, the 30 KB extract cap, and trailer-based claimant matching are visible product limitations. The UI must explain that a trailer proves only the matching rule used by the demo, not legal identity. It must keep a claim's appeal window visible and distinguish a recorded proof snapshot from a current read.

