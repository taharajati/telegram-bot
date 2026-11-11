import { NextRequest, NextResponse } from 'next/server';
import { requireSeller } from '@/lib/auth';
import { query } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const session = await requireSeller();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Get shop_id for this seller
    const owner = await query(
      'SELECT shop_id FROM shop_owners WHERE user_id = $1',
      [session.userId]
    );

    if (!owner || owner.length === 0) {
      return NextResponse.json({ error: 'Shop not found' }, { status: 404 });
    }

    const shopId = owner[0].shop_id;

    // Get categories for this shop
    const categories = await query(
      'SELECT id, name FROM categories WHERE shop_id = $1 ORDER BY name',
      [shopId]
    );

    return NextResponse.json(categories);

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
