// src/app/api/seller/shop-info/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { getShopOwner, getShopById } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const userId = parseInt(request.nextUrl.searchParams.get('user_id') || '0');
    if (!userId) return NextResponse.json({ error: 'Invalid' }, { status: 400 });

    const owner = await getShopOwner(userId);
    if (!owner) return NextResponse.json({ error: 'Not found' }, { status: 404 });

    const shop = await getShopById(owner.shop_id);
    return NextResponse.json({ shop_id: owner.shop_id, shop_name: shop?.name || 'فروشگاه' });
  } catch {
    return NextResponse.json({ error: 'Server error' }, { status: 500 });
  }
}