// src/lib/csrf.ts
// CSRF token generation and validation for Next.js API routes
// Uses SameSite=Lax cookie + CSRF token double-submit pattern

import { cookies } from 'next/headers';
import { createHash, randomBytes } from 'crypto';

const CSRF_COOKIE = 'fsh_csrf';
const TOKEN_LENGTH = 32;
const TOKEN_EXPIRY_MS = 30 * 60 * 1000; // 30 minutes

/**
 * Generate a new CSRF token, set it as a cookie, and return it.
 * The client must include this token in a custom header for POST requests.
 */
export async function generateCsrfToken(): Promise<string> {
  const raw = randomBytes(TOKEN_LENGTH).toString('hex');
  const token = createHash('sha256').update(raw).digest('hex');
  
  const cookieStore = await cookies();
  const isProduction = process.env.NODE_ENV === 'production';
  cookieStore.set(CSRF_COOKIE, token, {
    httpOnly: true,
    secure: isProduction,
    sameSite: 'strict',
    path: '/',
    maxAge: Math.floor(TOKEN_EXPIRY_MS / 1000),
  });
  
  return token;
}

/**
 * Validate that the CSRF token in the header matches the cookie.
 * Must be called from POST/PUT/PATCH/DELETE API routes only.
 */
export async function validateCsrf(request: Request): Promise<boolean> {
  // Only validate state-changing methods
  const method = request.method.toUpperCase();
  if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    return true; // GET/HEAD are safe
  }
  
  // Check X-CSRF-Token header
  const headerToken = request.headers.get('x-csrf-token');
  if (!headerToken) return false;
  
  // Check cookie token
  const cookieStore = await cookies();
  const cookieToken = cookieStore.get(CSRF_COOKIE)?.value;
  if (!cookieToken) return false;
  
  // Compare using timing-safe comparison
  if (headerToken.length !== cookieToken.length) return false;
  
  const a = Buffer.from(headerToken);
  const b = Buffer.from(cookieToken);
  return a.length === b.length && require('crypto').timingSafeEqual(a, b);
}

/**
 * Read CSRF token for use in API requests.
 * Returns null if no token exists (user needs to fetch one first).
 */
export async function getCsrfToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(CSRF_COOKIE)?.value || null;
}
