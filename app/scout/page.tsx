import source from "@/deploy/proof.json";
import type { Proof } from "@/lib/domain";
import Scout from "@/components/scout";

export const metadata = { title: "Scout an issue — Bounty Bench" };

export default function Page() {
  return <Scout proof={source as unknown as Proof} />;
}
