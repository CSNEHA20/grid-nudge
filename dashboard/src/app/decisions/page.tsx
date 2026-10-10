import { getDecisions } from "@/lib/data";
import { DecisionView } from "@/components/DecisionView";

export default async function DecisionsPage() {
  const decisions = await getDecisions();
  return <DecisionView decisions={decisions} initialId="d_002_safety_veto" />;
}
