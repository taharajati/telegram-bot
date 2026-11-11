// src/app/api/admin/orders/[id]/status/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { updateOrderStatus } from '@/lib/db';
import { requireAdmin } from '@/lib/auth';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    // 🔒 Auth check
    await requireAdmin();

    const { id } = await params;
    const formData = await request.formData();
    const status = formData.get('status') as string;
    const orderId = parseInt(id);

    if (!orderId || !status) {
      return NextResponse.json({ error: 'Invalid data' }, { status: 400 });
    }

    await updateOrderStatus(orderId, status, 'admin_web');
    return NextResponse.redirect(new URL(`/admin/orders/${orderId}`, request.url));
  } catch (error) {
    if (error instanceof Error && (error.message === 'Unauthorized' || error.message === 'Forbidden')) {
      return NextResponse.json({ error: error.message }, { status: error.message === 'Unauthorized' ? 401 : 403 });
    }
    console.error(error);
    return NextResponse.json({ error: 'Server error' }, { status: 500 });
  }
}
