// src/app/api/auth/login/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { getShopOwner, getUserById } from '@/lib/db';
import { setSession } from '@/lib/auth';
import bcrypt from 'bcrypt';

// ─── In-memory rate limiter ────────────────────────────
const loginAttempts = new Map<string, { count: number; blockedUntil: number }>();
const MAX_ATTEMPTS = 5;
const BLOCK_DURATION_MS = 15 * 60 * 1000; // 15 minutes
const WINDOW_MS = 10 * 60 * 1000; // 10 minutes sliding window

function checkRateLimit(identifier: string): { allowed: boolean; retryAfter?: number } {
  const now = Date.now();
  const entry = loginAttempts.get(identifier);

  // Check if currently blocked
  if (entry && entry.blockedUntil > now) {
    return { allowed: false, retryAfter: Math.ceil((entry.blockedUntil - now) / 1000) };
  }

  // Reset if window expired
  if (entry && now - WINDOW_MS > entry.blockedUntil) {
    loginAttempts.delete(identifier);
  }

  return { allowed: true };
}

function recordFailedAttempt(identifier: string) {
  const now = Date.now();
  const entry = loginAttempts.get(identifier) || { count: 0, blockedUntil: now };

  entry.count += 1;
  if (entry.count >= MAX_ATTEMPTS) {
    entry.blockedUntil = now + BLOCK_DURATION_MS;
    entry.count = 0;
    // Clear block after duration
    setTimeout(() => loginAttempts.delete(identifier), BLOCK_DURATION_MS);
  } else {
    entry.blockedUntil = now;
  }
  loginAttempts.set(identifier, entry);
}

function clearAttempts(identifier: string) {
  loginAttempts.delete(identifier);
}
// ────────────────────────────────────────────────────────

async function verifyPassword(password: string, storedHash: string): Promise<boolean> {
  // bcrypt hashes start with $2b$, $2a$, $2y$
  if (storedHash.startsWith('$2')) {
    return bcrypt.compare(password, storedHash);
  }
  // Legacy SHA-256 support (pre-bcrypt migration)
  // Old format: hash = sha256(salt + password), with password_salt stored separately
  // We can't verify without the salt — force them to reset via bot
  return false;
}

/**
 * Detect if stored hash is legacy SHA-256 (64 hex chars, not starting with $2).
 */
function isLegacyHash(storedHash: string): boolean {
  return /^[0-9a-f]{64}$/i.test(storedHash) && !storedHash.startsWith('$2');
}

export async function POST(req: NextRequest) {
  try {
    const { userId, password } = await req.json();
    const uid = parseInt(userId);
    if (!uid) {
      return NextResponse.json({ success: false, error: 'شناسه کاربری نامعتبر است.' });
    }

    // Rate limit check
    const rateKey = `login:${uid}`;
    const rateCheck = checkRateLimit(rateKey);
    if (!rateCheck.allowed) {
      return NextResponse.json({
        success: false,
        error: `تعداد تلاش‌های ناموفق زیاد شد. لطفاً ${Math.ceil(rateCheck.retryAfter! / 60)} دقیقه صبر کنید.`,
      }, { status: 429 });
    }

    const adminIds = (process.env.ADMIN_IDS || '').split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n));
    const isAdmin = adminIds.includes(uid);
    const owner = await getShopOwner(uid);

    // Determine required password: admin if admin, seller if seller
    const needsPassword = isAdmin || !!owner;

    if (needsPassword && !password) {
      return NextResponse.json({ success: false, error: isAdmin ? 'رمز عبور ادمین را وارد کنید.' : 'رمز عبور فروشنده را وارد کنید.', requirePassword: true });
    }

    // Try admin first
    if (isAdmin) {
      if (password === process.env.ADMIN_PASSWORD) {
        clearAttempts(rateKey);
        await setSession({ userId: uid, role: 'admin', loginMethod: 'telegram_id' });
        return NextResponse.json({ success: true, role: 'admin' });
      }
      // Admin password wrong — don't fall through to seller
      recordFailedAttempt(rateKey);
      return NextResponse.json({ success: false, error: 'رمز عبور اشتباه است.' });
    }

    // Try seller
    if (owner) {
      if (!owner.password_hash) {
        return NextResponse.json({ success: false, error: 'شما هنوز رمز عبور تنظیم نکرده‌اید. لطفاً در ربات فروشگرام یک رمز تنظیم کنید.' });
      }
      // Check for legacy SHA-256 hash that needs migration
      if (isLegacyHash(owner.password_hash)) {
        recordFailedAttempt(rateKey);
        return NextResponse.json({
          success: false,
          error: 'روش هش رمز عبور به‌روزرسانی شده. لطفاً در ربات فروشگرام (قسمت /my_panel) یک رمز جدید تنظیم کنید.',
          requireMigration: true,
        });
      }
      if (await verifyPassword(password, owner.password_hash)) {
        clearAttempts(rateKey);
        await setSession({
          userId: uid,
          role: 'seller',
          shopId: owner.shop_id,
          firstName: owner.first_name || undefined,
          loginMethod: 'telegram_id',
        });
        return NextResponse.json({ success: true, role: 'seller', shopId: owner.shop_id });
      }
      recordFailedAttempt(rateKey);
      return NextResponse.json({ success: false, error: isAdmin ? 'رمز عبور اشتباه است.' : 'رمز عبور فروشنده اشتباه است.' });
    }

    // Customer (no password needed)
    if (!needsPassword) {
      const user = await getUserById(uid);
      if (user) {
        await setSession({ userId: uid, role: 'customer', loginMethod: 'telegram_id' });
        return NextResponse.json({ success: true, role: 'customer' });
      }
    }

    return NextResponse.json({ success: false, error: 'کاربری با این شناسه یافت نشد. ابتدا در ربات ثبت‌نام کنید.' });
  } catch (e: unknown) {
    console.error('Login error:', e);
    return NextResponse.json({ success: false, error: 'خطای سرور' }, { status: 500 });
  }
}
