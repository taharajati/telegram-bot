// src/app/api/admin/create-claim-code/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { createClaimCode } from '@/lib/db';
import { requireAdmin } from '@/lib/auth';

export async function POST(request: NextRequest) {
  try {
    // 🔒 Auth check
    const session = await requireAdmin();

    const formData = await request.formData();
    const shopId = parseInt(formData.get('shop_id') as string);
    if (!shopId) return NextResponse.json({ error: 'Invalid shop_id' }, { status: 400 });

    const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
    await createClaimCode(shopId, session.userId, expiresAt);

    return NextResponse.redirect(new URL('/admin/claim-codes', request.url));
  } catch (error) {
    if (error instanceof Error && (error.message === 'Unauthorized' || error.message === 'Forbidden')) {
      return NextResponse.json({ error: error.message }, { status: error.message === 'Unauthorized' ? 401 : 403 });
    }
    console.error(error);
    return NextResponse.json({ error: 'Server error' }, { status: 500 });
  }
}
