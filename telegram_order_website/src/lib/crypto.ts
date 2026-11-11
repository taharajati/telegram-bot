// src/lib/crypto.ts
// Application-level encryption for sensitive bank data
// Uses AES-256-GCM with key derived from ENCRYPTION_KEY env var

import { createCipheriv, createDecipheriv, randomBytes, scryptSync } from 'crypto';

// Key derivation - uses ENCRYPTION_KEY from env (32 bytes = 256 bits)
const MASTER_KEY = process.env.ENCRYPTION_KEY;
if (!MASTER_KEY || MASTER_KEY.length < 32) {
  throw new Error('ENCRYPTION_KEY must be set in env (min 32 chars)');
}
const KEY = scryptSync(MASTER_KEY, 'foroshgram-salt', 32); // 256-bit key

const IV_LENGTH = 12; // GCM recommended 96-bit IV
const AUTH_TAG_LENGTH = 16;

/** Encrypt plaintext string → base64(ciphertext + iv + authTag) */
export function encrypt(plaintext: string): string {
  const iv = randomBytes(IV_LENGTH);
  const cipher = createCipheriv('aes-256-gcm', KEY, iv);
  const ciphertext = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const authTag = cipher.getAuthTag();
  // Store as: iv (12) + ciphertext + authTag (16) → all base64
  return Buffer.concat([iv, ciphertext, authTag]).toString('base64');
}

/** Decrypt base64 string → plaintext */
export function decrypt(encryptedB64: string): string {
  const data = Buffer.from(encryptedB64, 'base64');
  if (data.length < IV_LENGTH + AUTH_TAG_LENGTH + 1) {
    throw new Error('Invalid encrypted data length');
  }
  const iv = data.subarray(0, IV_LENGTH);
  const authTag = data.subarray(data.length - AUTH_TAG_LENGTH);
  const ciphertext = data.subarray(IV_LENGTH, data.length - AUTH_TAG_LENGTH);
  const decipher = createDecipheriv('aes-256-gcm', KEY, iv);
  decipher.setAuthTag(authTag);
  const plaintext = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  return plaintext.toString('utf8');
}

/** Check if a string looks like it's already encrypted (base64, correct length) */
export function isEncrypted(value: string): boolean {
  if (!value) return false;
  try {
    const buf = Buffer.from(value, 'base64');
    return buf.length >= IV_LENGTH + AUTH_TAG_LENGTH + 1;
  } catch {
    return false;
  }
}

/** Safe getter - decrypts if encrypted, returns plaintext */
export function safeDecrypt(value: string | null | undefined): string | null {
  if (!value) return null;
  if (isEncrypted(value)) {
    try {
      return decrypt(value);
    } catch {
      return value; // fallback if decrypt fails (legacy data)
    }
  }
  return value; // already plaintext
}

/** Safe setter - always encrypts non-empty values */
export function safeEncrypt(value: string | null | undefined): string | null {
  if (!value) return null;
  if (isEncrypted(value)) return value; // already encrypted
  return encrypt(value);
}