import { getTimelineData } from "@/lib/data";
import { LiveView } from "@/components/LiveView";

export default async function LivePage() {
  const timeline = await getTimelineData();
  return <LiveView initialTimeline={timeline} />;
}
