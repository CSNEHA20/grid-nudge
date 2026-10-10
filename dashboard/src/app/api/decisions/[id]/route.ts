import { NextRequest, NextResponse } from "next/server";
import { getDecisionById } from "@/lib/data";

export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const decision = await getDecisionById(params.id);
    if (!decision) {
      return NextResponse.json({ error: "Decision not found" }, { status: 404 });
    }
    return NextResponse.json(decision);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { error: "Failed to load decision", details: message },
      { status: 500 }
    );
  }
}
