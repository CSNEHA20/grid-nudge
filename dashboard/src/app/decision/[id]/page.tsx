import { getDecisions } from "@/lib/data";
import { DecisionView } from "@/components/DecisionView";

export default async function DecisionDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const decisions = await getDecisions();
  return <DecisionView decisions={decisions} initialId={params.id} />;
}
