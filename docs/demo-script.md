# Two-minute Bounty Bench demo

**0:00–0:15 — Board**  
Open the live app. Point to the StudioNet network badge, then open the main fixture bounty. Explain that the live queue comes from current contract reads; the separate proof panel links to the recorded release manifest.

**0:15–0:35 — Frozen spec**  
Show the three acceptance criteria and criteria hash. Open the repo and pinned base SHA. Note that the model cannot rewrite criteria after the bounty is funded.

**0:35–1:05 — Ordered claims**  
Walk the A–E queue in order. A reused D’s commit and fails the claimant trailer check. B fixes the behavior but fails the test criterion. C’s diff contains the instruction-like comment but does not fix the bug. The Board, rather than the model, controls the queue and bond accounting.

**1:05–1:35 — Evidence and settlement**  
Select D. Show each `MET` verdict, quote, digest, and the corresponding pinned GitHub diff. Open the PatchJudge transaction and explain that validators refetch the evidence. Show D’s finalized reward-plus-bond payout and E’s refunded bond. Show the three forfeited bonds reaching the funder.

**1:35–1:50 — Refund and timeout**  
Open the rejected-spec case and show the reason plus refund. Open the timeout case after its grace period and show the returned reward and any pending-bond refunds.

**1:50–2:00 — Limits**  
Close on the 30 KB evidence cap, GitHub availability, and trailer-based anti-copy limitation. Remind reviewers that Explorer proof and current reads are labeled separately.
