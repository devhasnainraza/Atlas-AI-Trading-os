import { NextRequest, NextResponse } from "next/server";
import crypto from "node:crypto";
import { getDatabase } from "../../../../lib/server/db";
import { hashPassword } from "../../../../lib/server/cryptoVault";
import { createSession } from "../../../../lib/server/session";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { email, password, name } = body;

    if (!email || !email.includes("@")) {
      return NextResponse.json({ error: "Valid email is required" }, { status: 400 });
    }
    if (!password || password.length < 6) {
      return NextResponse.json({ error: "Password must be at least 6 characters" }, { status: 400 });
    }

    const cleanEmail = email.trim().toLowerCase();
    const cleanName = (name || cleanEmail.split("@")[0]).trim();
    const db = getDatabase();

    // Check if user already exists
    const checkStmt = db.prepare("SELECT id FROM users WHERE email = ?");
    const existing = checkStmt.get(cleanEmail);
    if (existing) {
      return NextResponse.json({ error: "An account with this email already exists" }, { status: 409 });
    }

    const userId = "usr-" + crypto.randomBytes(8).toString("hex");
    const passwordHash = hashPassword(password);
    const createdAt = new Date().toISOString();

    const insertStmt = db.prepare(`
      INSERT INTO users (id, email, name, password_hash, created_at)
      VALUES (?, ?, ?, ?, ?)
    `);
    insertStmt.run(userId, cleanEmail, cleanName, passwordHash, createdAt);

    // Create session and set HTTP-only cookie
    const { token, expiresAt } = createSession(userId);

    const res = NextResponse.json({
      success: true,
      user: {
        id: userId,
        email: cleanEmail,
        name: cleanName,
        createdAt,
      },
    });

    res.cookies.set("atlas_session", token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      expires: expiresAt,
      path: "/",
    });

    return res;
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Registration failed" }, { status: 500 });
  }
}
