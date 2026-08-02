// src/app/api/admin/toggle-user-block/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { toggleUserBlocked } from '@/lib/db';
import { requireAdmin } from '@/lib/auth';

export async function POST(request: NextRequest) {
  try {
    // 🔒 Auth check
    await requireAdmin();

    const formData = await request.formData();
    const userId = parseInt(formData.get('user_id') as string);
    if (!userId) return NextResponse.json({ error: 'Invalid user_id' }, { status: 400 });
    
    await toggleUserBlocked(userId);
    return NextResponse.redirect(new URL('/admin/users', request.url));
  } catch (error) {
    if (error instanceof Error && (error.message === 'Unauthorized' || error.message === 'Forbidden')) {
      return NextResponse.json({ error: error.message }, { status: error.message === 'Unauthorized' ? 401 : 403 });
    }
    console.error(error);
    return NextResponse.json({ error: 'Server error' }, { status: 500 });
  }
}
