import { NextRequest, NextResponse } from "next/server";
import { getSessionUser } from "../../../../lib/server/session";
import { getDatabase } from "../../../../lib/server/db";

export async function POST(req: NextRequest) {
  try {
    const user = getSessionUser(req);
    if (!user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const { provider } = body;

    if (!provider) {
      return NextResponse.json({ error: "Provider is required" }, { status: 400 });
    }

    const db = getDatabase();
    const stmt = db.prepare("DELETE FROM user_credentials WHERE user_id = ? AND provider = ?");
    stmt.run(user.id, provider.toLowerCase());

    return NextResponse.json({ success: true, message: `Credential for ${provider} deleted` });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Failed to delete credential" }, { status: 500 });
  }
}
