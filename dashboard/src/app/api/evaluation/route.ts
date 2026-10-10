import { NextResponse } from "next/server";
import { getEvaluationData } from "@/lib/data";

export async function GET() {
  try {
    const data = await getEvaluationData();
    return NextResponse.json(data);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { error: "Failed to load evaluation data", details: message },
      { status: 500 }
    );
  }
}
