// src/app/api/admin/toggle-user-block/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { toggleUserBlocked } from '@/lib/db';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const userId = parseInt(formData.get('user_id') as string);
    if (!userId) return NextResponse.json({ error: 'Invalid' }, { status: 400 });
    await toggleUserBlocked(userId);
    return NextResponse.redirect(new URL('/admin/users', request.url));
  } catch {
    return NextResponse.json({ error: 'Server error' }, { status: 500 });
  }
}