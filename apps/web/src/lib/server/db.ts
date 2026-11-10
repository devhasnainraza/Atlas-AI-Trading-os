import { DatabaseSync } from "node:sqlite";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";

let dbInstance: DatabaseSync | null = null;

export function getDataDir(): string {
  // On Vercel, AWS Lambda, or container environments where process.cwd() is read-only:
  const isServerless =
    process.env.VERCEL === "1" ||
    Boolean(process.env.AWS_LAMBDA_FUNCTION_NAME) ||
    Boolean(process.env.LAMBDA_TASK_ROOT);

  if (isServerless) {
    const tmpDir = path.join(os.tmpdir(), "atlas_data");
    try {
      if (!fs.existsSync(tmpDir)) {
        fs.mkdirSync(tmpDir, { recursive: true });
      }
      return tmpDir;
    } catch {
      return os.tmpdir();
    }
  }

  // Local development directory
  const localDir = path.join(process.cwd(), "data");
  try {
    if (!fs.existsSync(localDir)) {
      fs.mkdirSync(localDir, { recursive: true });
    }
    return localDir;
  } catch {
    const tmpFallback = path.join(os.tmpdir(), "atlas_data");
    try {
      if (!fs.existsSync(tmpFallback)) {
        fs.mkdirSync(tmpFallback, { recursive: true });
      }
      return tmpFallback;
    } catch {
      return os.tmpdir();
    }
  }
}

export function getDatabase(): DatabaseSync {
  if (dbInstance) {
    return dbInstance;
  }

  const dataDir = getDataDir();
  const dbPath = path.join(dataDir, "atlas_secure.db");
  const db = new DatabaseSync(dbPath);

  // Enable WAL mode and foreign keys safely
  try {
    db.exec("PRAGMA journal_mode = WAL;");
  } catch {
    try {
      db.exec("PRAGMA journal_mode = DELETE;");
    } catch {
      // ignore
    }
  }
  try {
    db.exec("PRAGMA foreign_keys = ON;");
  } catch {
    // ignore
  }

  // Schema creation
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      email TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sessions (
      token TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      expires_at TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS user_credentials (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      provider TEXT NOT NULL,
      category TEXT NOT NULL, -- 'AI' or 'BROKER'
      encrypted_payload TEXT NOT NULL,
      iv TEXT NOT NULL,
      auth_tag TEXT NOT NULL,
      masked_key TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'ACTIVE',
      account_type TEXT DEFAULT 'LIVE',
      updated_at TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
      UNIQUE(user_id, provider)
    );

    CREATE TABLE IF NOT EXISTS user_journal (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      time TEXT NOT NULL,
      symbol TEXT NOT NULL,
      side TEXT NOT NULL,
      entry_price REAL NOT NULL,
      exit_price REAL NOT NULL,
      size_str TEXT NOT NULL,
      pnl_usd REAL NOT NULL,
      pnl_pct REAL NOT NULL,
      tags TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'CLOSED',
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS user_alerts (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      symbol TEXT NOT NULL,
      type TEXT NOT NULL,
      target_value REAL NOT NULL,
      current_value REAL NOT NULL,
      note TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'ACTIVE',
      created_at TEXT NOT NULL,
      sound_enabled INTEGER NOT NULL DEFAULT 1,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
  `);

  dbInstance = db;
  return dbInstance;
}
