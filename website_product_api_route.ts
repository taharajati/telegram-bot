import { NextRequest, NextResponse } from 'next/server';
import { requireSeller } from '@/lib/auth';
import { queryOne, getPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const session = await requireSeller();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { name, description, price, stock, category_id, images } = body;

    // Validation
    if (!name || !price || !stock || !category_id) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    // Get shop_id for this seller
    const owner = await queryOne(
      'SELECT shop_id FROM shop_owners WHERE user_id = $1',
      [session.userId]
    );

    if (!owner) {
      return NextResponse.json({ error: 'Shop not found' }, { status: 404 });
    }

    const pool = getPool();
    const client = await pool.connect();

    try {
      await client.query('BEGIN');

      // Insert product
      const result = await client.query(
        `INSERT INTO products (shop_id, category_id, name, description, price, stock, image_url, is_active)
         VALUES ($1, $2, $3, $4, $5, $6, $7, true)
         RETURNING id`,
        [owner.shop_id, category_id, name, description || null, price, stock, images[0] || null]
      );

      const productId = result.rows[0].id;

      // Insert additional images into product_images table
      if (images && images.length > 1) {
        for (let i = 1; i < images.length; i++) {
          await client.query(
            'INSERT INTO product_images (product_id, image_url, sort_order) VALUES ($1, $2, $3)',
            [productId, images[i], i]
          );
        }
      }

      await client.query('COMMIT');

      return NextResponse.json({ success: true, product_id: productId });

    } catch (error) {
      await client.query('ROLLBACK');
      console.error('Product creation error:', error);
      return NextResponse.json({ error: 'Failed to create product' }, { status: 500 });
    } finally {
      client.release();
    }

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
