import { getTimelineData } from "@/lib/data";
import { LiveView } from "@/components/LiveView";

export default async function HomePage() {
  const timeline = await getTimelineData();
  return <LiveView initialTimeline={timeline} />;
}
