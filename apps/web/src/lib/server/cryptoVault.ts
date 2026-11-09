import crypto from "node:crypto";
import path from "node:path";
import fs from "node:fs";

// Master encryption key management
function getMasterVaultKey(): Buffer {
  const envKey = process.env.ATLAS_VAULT_MASTER_KEY;
  if (envKey && envKey.length >= 32) {
    return crypto.scryptSync(envKey, "atlas-vault-salt", 32);
  }

  // Fallback to local server-only persistent vault secret file
  const dataDir = path.join(process.cwd(), "data");
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  const keyFilePath = path.join(dataDir, ".vault_key");
  if (fs.existsSync(keyFilePath)) {
    const raw = fs.readFileSync(keyFilePath, "utf8").trim();
    return Buffer.from(raw, "hex");
  }

  // Generate high-entropy 256-bit random master key and save with restricted file permissions
  const newKey = crypto.randomBytes(32);
  fs.writeFileSync(keyFilePath, newKey.toString("hex"), { mode: 0o600 });
  return newKey;
}

export interface EncryptedVaultPayload {
  encryptedData: string;
  iv: string;
  authTag: string;
}

/**
 * Encrypt arbitrary sensitive string (API Key, Secret, etc.) with AES-256-GCM
 */
export function encryptVaultSecret(plaintext: string): EncryptedVaultPayload {
  const masterKey = getMasterVaultKey();
  const iv = crypto.randomBytes(12); // Standard 96-bit IV for GCM
  const cipher = crypto.createCipheriv("aes-256-gcm", masterKey, iv);

  let encrypted = cipher.update(plaintext, "utf8", "hex");
  encrypted += cipher.final("hex");
  const authTag = cipher.getAuthTag().toString("hex");

  return {
    encryptedData: encrypted,
    iv: iv.toString("hex"),
    authTag,
  };
}

/**
 * Decrypt AES-256-GCM encrypted payload back to plaintext in-memory
 */
export function decryptVaultSecret(payload: EncryptedVaultPayload): string {
  const masterKey = getMasterVaultKey();
  const iv = Buffer.from(payload.iv, "hex");
  const decipher = crypto.createDecipheriv("aes-256-gcm", masterKey, iv);
  decipher.setAuthTag(Buffer.from(payload.authTag, "hex"));

  let decrypted = decipher.update(payload.encryptedData, "hex", "utf8");
  decrypted += decipher.final("utf8");
  return decrypted;
}

/**
 * Create masked display string for credentials (e.g. gsk_••••••••••••48Pc)
 */
export function maskCredential(key: string): string {
  if (!key || key.length < 8) return "••••••••";
  const start = key.slice(0, 4);
  const end = key.slice(-4);
  return `${start}••••••••••••${end}`;
}

/**
 * Hash password with PBKDF2 (100,000 iterations, SHA-512)
 */
export function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16).toString("hex");
  const derived = crypto.pbkdf2Sync(password, salt, 100000, 64, "sha512").toString("hex");
  return `${salt}:${derived}`;
}

/**
 * Verify password against stored hash using constant-time comparison
 */
export function verifyPassword(password: string, storedHash: string): boolean {
  try {
    const parts = storedHash.split(":");
    if (parts.length !== 2) return false;
    const [salt, hash] = parts;
    if (!salt || !hash) return false;
    const derived = crypto.pbkdf2Sync(password, salt, 100000, 64, "sha512").toString("hex");
    return crypto.timingSafeEqual(Buffer.from(hash, "hex"), Buffer.from(derived, "hex"));
  } catch {
    return false;
  }
}
