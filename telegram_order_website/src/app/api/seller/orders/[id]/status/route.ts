// src/app/api/seller/orders/[id]/status/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { updateOrderStatus } from '@/lib/db';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const formData = await request.formData();
    const status = formData.get('status') as string;
    const orderId = parseInt(id);
    if (!orderId || !status) return NextResponse.json({ error: 'Invalid' }, { status: 400 });
    await updateOrderStatus(orderId, status, 'seller_web');
    return NextResponse.redirect(new URL(`/seller/orders/${orderId}`, request.url));
  } catch {
    return NextResponse.json({ error: 'Server error' }, { status: 500 });
  }
}