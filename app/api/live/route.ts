import { snapshot } from "@/lib/server-chain";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    return Response.json(await snapshot(), {
      headers: { "Cache-Control": "public, s-maxage=15, stale-while-revalidate=15" },
    });
  } catch (error) {
    return Response.json(
      { bounties: [], readAt: new Date().toISOString(), network: "StudioNet", chainId: 61999, error: error instanceof Error ? error.message : "Live reads are unavailable." },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
}
