import { NextRequest, NextResponse } from 'next/server';
import { requireSeller } from '@/lib/auth';
import { queryOne, getPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

// GET: Get product details
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await requireSeller();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const productId = parseInt(params.id);
    
    // Get product with images
    const product = await queryOne(
      `SELECT p.*, 
              ARRAY_AGG(pi.image_url ORDER BY pi.sort_order) FILTER (WHERE pi.image_url IS NOT NULL) as additional_images
       FROM products p
       LEFT JOIN product_images pi ON p.id = pi.product_id
       WHERE p.id = $1
       GROUP BY p.id`,
      [productId]
    );

    if (!product) {
      return NextResponse.json({ error: 'Product not found' }, { status: 404 });
    }

    // Combine main image and additional images
    const allImages = [
      product.image_url,
      ...(product.additional_images || [])
    ].filter(Boolean);

    return NextResponse.json({
      ...product,
      images: allImages,
    });

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

// PUT: Update product
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await requireSeller();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const productId = parseInt(params.id);
    const body = await request.json();
    const { name, description, price, stock, category_id, images } = body;

    // Verify ownership
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

      // Update product
      await client.query(
        `UPDATE products 
         SET name = $1, description = $2, price = $3, stock = $4, 
             category_id = $5, image_url = $6, updated_at = NOW()
         WHERE id = $7 AND shop_id = $8`,
        [name, description || null, price, stock, category_id, images[0] || null, productId, owner.shop_id]
      );

      // Delete old additional images
      await client.query('DELETE FROM product_images WHERE product_id = $1', [productId]);

      // Insert new additional images
      if (images && images.length > 1) {
        for (let i = 1; i < images.length; i++) {
          await client.query(
            'INSERT INTO product_images (product_id, image_url, sort_order) VALUES ($1, $2, $3)',
            [productId, images[i], i - 1]
          );
        }
      }

      await client.query('COMMIT');

      return NextResponse.json({ success: true });

    } catch (error) {
      await client.query('ROLLBACK');
      console.error('Product update error:', error);
      return NextResponse.json({ error: 'Failed to update product' }, { status: 500 });
    } finally {
      client.release();
    }

  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
