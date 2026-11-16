import source from "@/deploy/proof.json";
import type { Proof } from "@/lib/domain";
import BountyDetail from "@/components/bounty-detail";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <BountyDetail bountyId={decodeURIComponent(id)} proof={source as unknown as Proof} />;
}
