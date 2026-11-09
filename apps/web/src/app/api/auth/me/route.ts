import { NextRequest, NextResponse } from "next/server";
import { getSessionUser } from "../../../../lib/server/session";

export async function GET(req: NextRequest) {
  const user = getSessionUser(req);
  if (!user) {
    return NextResponse.json({ authenticated: false, user: null }, { status: 200 });
  }

  return NextResponse.json({
    authenticated: true,
    user,
  });
}
