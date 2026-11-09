import { NextRequest, NextResponse } from "next/server";
import { destroySession } from "../../../../lib/server/session";

export async function POST(req: NextRequest) {
  const token = req.cookies.get("atlas_session")?.value;
  if (token) {
    destroySession(token);
  }

  const res = NextResponse.json({ success: true, message: "Logged out successfully" });
  res.cookies.delete("atlas_session");
  return res;
}
