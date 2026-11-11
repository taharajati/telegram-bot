// src/app/api/seller/toggle-product/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { toggleProductActive } from '@/lib/db';
import { requireSeller } from '@/lib/auth';
import { validateCsrf } from '@/lib/csrf';

export async function POST(request: NextRequest) {
  try {
    await requireSeller();
    
    // CSRF validation
    if (!(await validateCsrf(request))) {
      return NextResponse.json({ error: 'Invalid CSRF token' }, { status: 403 });
    }
    
    const formData = await request.formData();
    const productId = parseInt(formData.get('product_id') as string);
    if (!productId) return NextResponse.json({ error: 'Invalid' }, { status: 400 });
    
    await toggleProductActive(productId);
    return NextResponse.redirect(new URL('/seller/products', request.url));
  } catch {
    return NextResponse.json({ error: 'Server error' }, { status: 500 });
  }
}