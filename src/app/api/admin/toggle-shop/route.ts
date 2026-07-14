// src/app/api/admin/toggle-shop/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { toggleShopActive } from '@/lib/db';
import { requireAdmin } from '@/lib/auth';
import { validateCsrf } from '@/lib/csrf';

export async function POST(request: NextRequest) {
  try {
    await requireAdmin();
    
    // CSRF validation
    if (!(await validateCsrf(request))) {
      return NextResponse.json({ error: 'Invalid CSRF token' }, { status: 403 });
    }
    
    const formData = await request.formData();
    const id = parseInt(formData.get('id') as string);
    if (!id) return NextResponse.json({ error: 'Invalid id' }, { status: 400 });
    
    await toggleShopActive(id);
    return NextResponse.redirect(new URL('/admin/shops', request.url));
  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: 'Server error' }, { status: 500 });
  }
}