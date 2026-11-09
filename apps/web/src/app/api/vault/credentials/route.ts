import { NextRequest, NextResponse } from "next/server";
import { getSessionUser } from "../../../../lib/server/session";
import { getDatabase } from "../../../../lib/server/db";

export async function GET(req: NextRequest) {
  const user = getSessionUser(req);
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = getDatabase();
  const stmt = db.prepare(`
    SELECT id, provider, category, masked_key, status, account_type, updated_at
    FROM user_credentials
    WHERE user_id = ?
    ORDER BY updated_at DESC
  `);

  const credentials = stmt.all(user.id);
  return NextResponse.json({ credentials });
}
