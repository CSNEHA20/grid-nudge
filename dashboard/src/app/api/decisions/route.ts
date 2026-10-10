import { NextResponse } from "next/server";
import { getDecisions } from "@/lib/data";

export async function GET() {
  try {
    const decisions = await getDecisions();
    return NextResponse.json(decisions);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { error: "Failed to load decisions", details: message },
      { status: 500 }
    );
  }
}
