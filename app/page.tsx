import source from "@/deploy/proof.json";
import type { Proof } from "@/lib/domain";
import Bench from "@/components/bench";

export default function Page() {
  return <Bench proof={source as unknown as Proof} />;
}
