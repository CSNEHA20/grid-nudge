import { NextResponse } from "next/server";
import { getTimelineData } from "@/lib/data";

export async function GET() {
  try {
    const data = await getTimelineData();
    return NextResponse.json(data);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { error: "Failed to load timeline data", details: message },
      { status: 500 }
    );
  }
}
