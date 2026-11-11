// src/app/api/auth/change-password/route.ts
import { NextRequest, NextResponse } from 'next/server';
import bcrypt from 'bcryptjs';
import { requireAuth } from '@/lib/auth';
import { getSellerByUserId, getAdminByUserId, setSellerPassword, setAdminPassword } from '@/lib/db';

export async function POST(request: NextRequest) {
  try {
    const session = await requireAuth();
    const body = await request.json();
    const { currentPassword, newPassword } = body;

    if (!currentPassword || !newPassword) {
      return NextResponse.json(
        { error: 'رمز فعلی و رمز جدید الزامی است' },
        { status: 400 }
      );
    }

    if (newPassword.length < 6) {
      return NextResponse.json(
        { error: 'رمز جدید باید حداقل ۶ کاراکتر باشد' },
        { status: 400 }
      );
    }

    if (session.role === 'admin') {
      const admin = await getAdminByUserId(session.userId);
      if (!admin || !admin.password_hash) {
        return NextResponse.json(
          { error: 'حساب ادمین یافت نشد' },
          { status: 404 }
        );
      }
      const valid = await bcrypt.compare(currentPassword, admin.password_hash);
      if (!valid) {
        return NextResponse.json(
          { error: 'رمز فعلی اشتباه است' },
          { status: 401 }
        );
      }
      const hashed = await bcrypt.hash(newPassword, 12);
      await setAdminPassword(session.userId, hashed);
      return NextResponse.json({ success: true });
    }

    if (session.role === 'seller') {
      const seller = await getSellerByUserId(session.userId);
      if (!seller || !seller.password_hash) {
        return NextResponse.json(
          { error: 'حساب فروشنده یافت نشد' },
          { status: 404 }
        );
      }
      const valid = await bcrypt.compare(currentPassword, seller.password_hash);
      if (!valid) {
        return NextResponse.json(
          { error: 'رمز فعلی اشتباه است' },
          { status: 401 }
        );
      }
      const hashed = await bcrypt.hash(newPassword, 12);
      await setSellerPassword(session.userId, hashed, '');
      return NextResponse.json({ success: true });
    }

    return NextResponse.json(
      { error: 'نقش نامعتبر' },
      { status: 403 }
    );
  } catch (err) {
    console.error('Change password error:', err);
    return NextResponse.json(
      { error: 'خطای سرور' },
      { status: 500 }
    );
  }
}
