import { scoutSnapshot } from "@/lib/server-chain";
import type { ScoutSnapshot } from "@/lib/domain";

export const dynamic = "force-dynamic";

// Last good IssueScout read, served while fresh and as a stale fallback when StudioNet rate-limits.
const FRESH_MS = 45_000;
let lastGood: { at: number; value: ScoutSnapshot } | null = null;

export async function GET() {
  const headers = { "Cache-Control": "no-store" };
  if (lastGood && Date.now() - lastGood.at < FRESH_MS) return Response.json(lastGood.value, { headers });
  try {
    const value = await scoutSnapshot();
    lastGood = { at: Date.now(), value };
    return Response.json(value, { headers });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Scout reads are unavailable.";
    if (lastGood) return Response.json({ ...lastGood.value, stale: true, error: `Live read unavailable (${message}). Showing the last good read.` }, { headers });
    return Response.json({ drafts: [], readAt: new Date().toISOString(), stale: true, error: `Live read unavailable (${message}). Showing recorded drafts.` }, { status: 503, headers });
  }
}
