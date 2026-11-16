import { snapshot } from "@/lib/server-chain";
import type { Snapshot } from "@/lib/domain";

export const dynamic = "force-dynamic";

// Last good StudioNet read, kept per server instance. Served while fresh, and as
// a stale fallback when StudioNet rate-limits or fails (429/500/503).
const FRESH_MS = 60_000;
let lastGood: { at: number; value: Snapshot } | null = null;

export async function GET() {
  const headers = { "Cache-Control": "no-store" };
  if (lastGood && Date.now() - lastGood.at < FRESH_MS) {
    return Response.json(lastGood.value, { headers });
  }
  try {
    const value = await snapshot();
    lastGood = { at: Date.now(), value };
    return Response.json(value, { headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Live reads are unavailable.";
    if (lastGood) {
      return Response.json(
        { ...lastGood.value, stale: true, staleSince: new Date(lastGood.at).toISOString(), error: `Live read unavailable (${message}). Showing the last good read.` },
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
