export type Preflight = { ok: boolean; title: string; detail: string };

// Mirrors the Board's identity check: a full line `Bounty-Claimant: <address>` (case-insensitive)
// must appear in the commit messages between the pinned base and the claimed head.
export async function preflightClaim(repo: string, base: string, head: string, claimant: string): Promise<Preflight> {
  if (!/^[0-9a-f]{40}$/i.test(head)) return { ok: false, title: "Not a commit SHA", detail: "Paste the full 40-character SHA of your last commit." };
  let response: Response;
  try {
    response = await fetch(`https://api.github.com/repos/${repo}/compare/${base}...${head}`, { headers: { Accept: "application/vnd.github+json" } });
  } catch {
    return { ok: false, title: "GitHub is unreachable", detail: "Check your connection and try again." };
  }
  if (response.status === 404) return { ok: false, title: "GitHub cannot compare these commits", detail: "Push your branch to a public fork first, then paste the SHA again." };
  if (response.status === 403) return { ok: false, title: "GitHub rate limit reached", detail: "Wait a few minutes. The on-chain check does not use this limit." };
  if (!response.ok) return { ok: false, title: `GitHub returned ${response.status}`, detail: "Try again shortly." };
  const data = await response.json() as { merge_base_commit?: { sha?: string }; ahead_by?: number; files?: unknown[]; commits?: { commit: { message: string } }[] };
  if (data.merge_base_commit?.sha?.toLowerCase() !== base.toLowerCase()) return { ok: false, title: "Your branch does not start at the pinned base", detail: `Create it from ${base.slice(0, 10)} so the diff is judged against the right code.` };
  const expected = `bounty-claimant: ${claimant}`.toLowerCase();
  const found = (data.commits ?? []).some((item) => item.commit.message.split(/\r?\n/).some((line) => line.trim().toLowerCase() === expected));
  if (!found) return { ok: false, title: "Claimant line not found", detail: `No commit between the base and your head has the line "Bounty-Claimant: ${claimant}". Without it the claim forfeits its bond.` };
  return { ok: true, title: "Ready to claim", detail: `${data.ahead_by ?? 0} commit${data.ahead_by === 1 ? "" : "s"}, ${data.files?.length ?? 0} file${data.files?.length === 1 ? "" : "s"} changed, claimant line found for your wallet.` };
}

export async function fundTestAccount(address: string) {
  const response = await fetch("https://studio.genlayer.com/api", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "sim_fundAccount", params: [address, 1_000_000_000_000_000_000] }),
  });
  const body = await response.json() as { error?: { message?: string } };
  if (body.error) throw Error(body.error.message ?? "The StudioNet faucet refused this request.");
}
