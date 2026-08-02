// src/lib/auth.ts
// JWT-based role system for Foroshgram
// No external auth library — just jose + cookies
//
// Security improvements:
// - requireSeller() re-checks shop.active from DB (not just JWT)
// - requireAdmin() re-checks admin exists in DB

import { SignJWT, jwtVerify } from 'jose';
import { cookies } from 'next/headers';
import { getShopById, getAdminByUserId } from '@/lib/db';

const SECRET = new TextEncoder().encode(process.env.JWT_SECRET || (() => { throw new Error('JWT_SECRET is not set'); })());
const COOKIE_NAME = 'fsh_session';
const EXPIRY = '7d';

export type UserRole = 'admin' | 'seller' | 'customer';

export interface SessionPayload {
  userId: number;
  role: UserRole;
  shopId?: number;
  firstName?: string;
  loginMethod: 'telegram_id' | 'username';
}

export async function signSession(payload: SessionPayload): Promise<string> {
  return new SignJWT(payload as any)
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime(EXPIRY)
    .sign(SECRET);
}

export async function verifySession(token: string): Promise<SessionPayload | null> {
  try {
    const { payload } = await jwtVerify(token, SECRET);
    return payload as unknown as SessionPayload;
  } catch {
    return null;
  }
}

export async function getSession(): Promise<SessionPayload | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
  if (!token) return null;
  return verifySession(token);
}

export async function setSession(payload: SessionPayload) {
  const token = await signSession(payload);
  const cookieStore = await cookies();
  const isProduction = process.env.NODE_ENV === 'production';
  cookieStore.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: isProduction, // HTTPS required in production
    sameSite: isProduction ? 'strict' : 'lax',     // CSRF protection: blocks cross-origin POST
    path: '/',
    maxAge: 7 * 24 * 60 * 60,
  });
}

export async function clearSession() {
  const cookieStore = await cookies();
  cookieStore.delete(COOKIE_NAME);
}

// ─── Role Helpers ─────────────────────────────────────────
export async function requireAuth(): Promise<SessionPayload> {
  const session = await getSession();
  if (!session) {
    throw new Error('Unauthorized');
  }
  return session;
}

export async function requireAdmin(): Promise<SessionPayload> {
  const session = await requireAuth();
  if (session.role !== 'admin') {
    throw new Error('Forbidden');
  }
  // Re-check: is this admin still in the admins table?
  const admin = await getAdminByUserId(session.userId);
  if (!admin) {
    throw new Error('Forbidden'); // admin record deleted
  }
  return session;
}

export async function requireSeller(): Promise<SessionPayload> {
  const session = await requireAuth();
  if (session.role !== 'seller' && session.role !== 'admin') {
    throw new Error('Forbidden');
  }
  // For sellers: re-check shop is still active
  if (session.role === 'seller' && session.shopId) {
    const shop = await getShopById(session.shopId);
    if (!shop || !shop.is_active) {
      throw new Error('ShopInactive'); // shop suspended or deleted
    }
  }
  return session;
}