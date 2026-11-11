// src/app/api/auth/login/route.ts
import { NextRequest, NextResponse } from 'next/server';
import bcrypt from 'bcryptjs';
import { signSession, setSessionCookie } from '@/lib/auth';
import { getSellerByUsername, getAdminByUserId } from '@/lib/db';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { username, password } = body;

    if (!username || !password) {
      return NextResponse.json(
        { error: 'نام کاربری و رمز عبور الزامی است' },
        { status: 400 }
      );
    }

    // Try seller login by username
    const seller = await getSellerByUsername(username);
    if (seller && seller.password_hash) {
      const valid = await bcrypt.compare(password, seller.password_hash);
      if (valid) {
        const token = await signSession({
          userId: seller.user_id,
          role: 'seller',
          shopId: seller.shop_id,
          loginMethod: 'username',
        });
        const res = NextResponse.json({ success: true, role: 'seller' });
        await setSessionCookie(res, {
          userId: seller.user_id,
          role: 'seller',
          shopId: seller.shop_id,
          loginMethod: 'username',
        });
        return res;
      }
    }

    // Try admin login (admin uses telegram_id as username)
    const numericId = /^\d+$/.test(username) ? parseInt(username, 10) : NaN;
    if (!Number.isNaN(numericId)) {
      const admin = await getAdminByUserId(numericId);
      if (admin && admin.password_hash) {
        const valid = await bcrypt.compare(password, admin.password_hash);
        if (valid) {
          await signSession({
            userId: admin.user_id,
            role: 'admin',
            loginMethod: 'username',
          });
          const res = NextResponse.json({ success: true, role: 'admin' });
          await setSessionCookie(res, {
            userId: admin.user_id,
            role: 'admin',
            loginMethod: 'username',
          });
          return res;
        }
      }
    }

    return NextResponse.json(
      { error: 'نام کاربری یا رمز عبور اشتباه است' },
      { status: 401 }
    );
  } catch (err) {
    console.error('Login error:', err);
    return NextResponse.json(
      { error: 'خطای سرور' },
      { status: 500 }
    );
  }
}