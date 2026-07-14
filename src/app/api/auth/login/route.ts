// src/app/api/auth/login/route.ts
// Login endpoint with rate limiting (Redis-backed) + bcrypt + SHA-256 legacy detection
import { NextRequest, NextResponse } from 'next/server';
import { getShopOwner, getUserById, getAdminByUserId } from '@/lib/db';
import { setSession } from '@/lib/auth';
import { checkLoginRateLimit, recordFailedLogin, clearLoginRateLimit } from '@/lib/rate-limiter';
import bcrypt from 'bcrypt';

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

    // Rate limit check (Redis-backed, survives restarts)
    const rateKey = `login:${uid}`;
    const rateCheck = await checkLoginRateLimit(rateKey);
    if (!rateCheck.allowed) {
      return NextResponse.json({
        success: false,
        error: `تعداد تلاش‌های ناموفق زیاد شد. لطفاً ${Math.ceil(rateCheck.retryAfterSeconds! / 60)} دقیقه صبر کنید.`,
      }, { status: 429 });
    }

    const owner = await getShopOwner(uid);
    const adminRecord = await getAdminByUserId(uid);
    const isAdmin = !!adminRecord;

    // Determine required password: admin if admin, seller if seller
    const needsPassword = isAdmin || !!owner;

    if (needsPassword && !password) {
      return NextResponse.json({ success: false, error: isAdmin ? 'رمز عبور ادمین را وارد کنید.' : 'رمز عبور فروشنده را وارد کنید.', requirePassword: true });
    }

    // Try admin first (from DB)
    if (isAdmin) {
      if (await verifyPassword(password, adminRecord.password_hash)) {
        // Enforce password change if flag is set
        if (adminRecord.must_change_password) {
          return NextResponse.json({ success: false, mustChangePassword: true, role: 'admin', error: 'لطفاً یک رمز عبور جدید تنظیم کنید.' });
        }
        await clearLoginRateLimit(rateKey);
        await setSession({ userId: uid, role: 'admin', loginMethod: 'telegram_id' });
        return NextResponse.json({ success: true, role: 'admin' });
      }
      // Admin password wrong — don't fall through to seller
      await recordFailedLogin(rateKey);
      return NextResponse.json({ success: false, error: 'رمز عبور اشتباه است.' });
    }

    // Try seller
    if (owner) {
      if (!owner.password_hash) {
        return NextResponse.json({ success: false, error: 'شما هنوز رمز عبور تنظیم نکرده‌اید. لطفاً در ربات فروشگرام یک رمز تنظیم کنید.' });
      }
      // Check for legacy SHA-256 hash that needs migration
      if (isLegacyHash(owner.password_hash)) {
        await recordFailedLogin(rateKey);
        return NextResponse.json({
          success: false,
          error: 'روش هش رمز عبور به‌روزرسانی شده. لطفاً در ربات فروشگرام (قسمت /my_panel) یک رمز جدید تنظیم کنید.',
          requireMigration: true,
        });
      }
      if (await verifyPassword(password, owner.password_hash)) {
        // Enforce password change if flag is set
        if (owner.must_change_password) {
          return NextResponse.json({ success: false, mustChangePassword: true, role: 'seller', shopId: owner.shop_id, error: 'لطفاً یک رمز عبور جدید تنظیم کنید.' });
        }
        await clearLoginRateLimit(rateKey);
        await setSession({
          userId: uid,
          role: 'seller',
          shopId: owner.shop_id,
          firstName: owner.first_name || undefined,
          loginMethod: 'telegram_id',
        });
        return NextResponse.json({ success: true, role: 'seller', shopId: owner.shop_id });
      }
      await recordFailedLogin(rateKey);
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
