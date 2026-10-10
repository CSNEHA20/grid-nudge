import { NextResponse } from "next/server";
import { getCalibrationData } from "@/lib/data";

export async function GET() {
  try {
    const data = await getCalibrationData();
    return NextResponse.json(data);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { error: "Failed to load calibration data", details: message },
      { status: 500 }
    );
  }
}
