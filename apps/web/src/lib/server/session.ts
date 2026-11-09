import { NextRequest } from "next/server";
import crypto from "node:crypto";
import { getDatabase } from "./db";

export interface SafeUser {
  id: string;
  email: string;
  name: string;
  createdAt: string;
}

export function createSession(userId: string): { token: string; expiresAt: Date } {
  const db = getDatabase();
  const token = crypto.randomBytes(32).toString("hex");
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days

  const stmt = db.prepare(`
    INSERT INTO sessions (token, user_id, expires_at)
    VALUES (?, ?, ?)
  `);
  stmt.run(token, userId, expiresAt.toISOString());

  return { token, expiresAt };
}

export function destroySession(token: string): void {
  const db = getDatabase();
  const stmt = db.prepare("DELETE FROM sessions WHERE token = ?");
  stmt.run(token);
}

export function getSessionUser(req: NextRequest): SafeUser | null {
  const token = req.cookies.get("atlas_session")?.value;
  if (!token) return null;

  const db = getDatabase();
  const stmt = db.prepare(`
    SELECT u.id, u.email, u.name, u.created_at, s.expires_at
    FROM sessions s
    JOIN users u ON s.user_id = u.id
    WHERE s.token = ?
  `);

  const row = stmt.get(token) as any;
  if (!row) return null;

  // Check expiration
  if (new Date(row.expires_at).getTime() < Date.now()) {
    destroySession(token);
    return null;
  }

  return {
    id: row.id,
    email: row.email,
    name: row.name,
    createdAt: row.created_at,
  };
}
