import { snapshot } from "@/lib/server-chain";
import type { Snapshot } from "@/lib/domain";

export const dynamic = "force-dynamic";

// Last good StudioNet read per view (board list, or one bounty with full detail), kept per server
// instance. Served while fresh, and as a stale fallback when StudioNet rate-limits or fails.
const FRESH_MS = 60_000;
const lastGood = new Map<string, { at: number; value: Snapshot }>();

export async function GET(request: Request) {
  const headers = { "Cache-Control": "no-store" };
  const id = new URL(request.url).searchParams.get("id") ?? "";
  const key = /^bounty-\d{1,6}$/.test(id) ? id : "";
  const cached = lastGood.get(key);
  if (cached && Date.now() - cached.at < FRESH_MS) return Response.json(cached.value, { headers });
  try {
    const value = await snapshot(key || undefined);
    lastGood.set(key, { at: Date.now(), value });
    return Response.json(value, { headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Live reads are unavailable.";
    const fallback = cached ?? lastGood.get("");
    if (fallback) {
      return Response.json(
        { ...fallback.value, stale: true, staleSince: new Date(fallback.at).toISOString(), error: `Live read unavailable (${message}). Showing the last good read.` },
        { headers },
      );
    }
    // Cold start with no good read yet: report unavailable so the page falls back to recorded proof.
    return Response.json(
      { bounties: [], readAt: new Date().toISOString(), network: "StudioNet", chainId: 61999, stale: true, error: `Live read unavailable (${message}). Showing recorded proof.` },
      { status: 503, headers },
    );
  }
}
