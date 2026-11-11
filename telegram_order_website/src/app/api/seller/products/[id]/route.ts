import { NextRequest, NextResponse } from 'next/server';
import { requireSeller } from '@/lib/auth';
import { queryOne, query, getPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

// GET: Get product details
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await requireSeller();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = await params;
    const productId = parseInt(id);
    
    // Get product with additional image file_ids + local urls
    const product = await queryOne(
      `SELECT p.*, 
              ARRAY_AGG(pi.file_id ORDER BY pi.sort_order) FILTER (WHERE pi.file_id IS NOT NULL) as additional_file_ids,
              ARRAY_AGG(pi.local_url ORDER BY pi.sort_order) FILTER (WHERE pi.local_url IS NOT NULL) as additional_images
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
    // For legacy products with only telegram file_ids, build API URLs for display
    const mainImage = product.image_url
      || (product.image_file_id ? `/api/product-image/${product.id}` : null);
    const additionalImages = product.additional_images || [];
    // Legacy additional images with only file_id → API URLs too
    const legacyExtra = (product.additional_file_ids || [])
      .filter((_: string, i: number) => !additionalImages[i])
      .map((_: string, i: number) => `/api/product-image/${product.id}?extra=${i}`);
    const allImages = [
      mainImage,
      ...additionalImages,
      ...legacyExtra,
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
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await requireSeller();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = await params;
    const productId = parseInt(id);
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

      // If the main image is a legacy API URL (from file_id), keep existing image_url
      let mainImageUrl = images[0] || null;
      if (mainImageUrl && mainImageUrl.startsWith('/api/product-image/')) {
        const existing = await client.query('SELECT image_url FROM products WHERE id = $1', [productId]);
        mainImageUrl = existing.rows[0]?.image_url || null;
      }

      // Update product
      await client.query(
        `UPDATE products 
         SET name = $1, description = $2, price = $3, stock = $4, 
             category_id = $5, image_url = $6, updated_at = NOW()
         WHERE id = $7 AND shop_id = $8`,
        [name, description || null, price, stock, category_id, mainImageUrl, productId, owner.shop_id]
      );

      // Delete old additional images
      await client.query('DELETE FROM product_images WHERE product_id = $1', [productId]);

      // Insert new additional images
      if (images && images.length > 1) {
        for (let i = 1; i < images.length; i++) {
          const imgUrl = images[i];
          // file_id is NOT NULL in DB; use local_url as file_id for web-uploaded images
          const fileId = imgUrl.startsWith('/api/product-image/')
            ? `legacy_${Date.now()}_${i}`
            : imgUrl;
          await client.query(
            'INSERT INTO product_images (product_id, file_id, local_url, sort_order) VALUES ($1, $2, $3, $4)',
            [productId, fileId, imgUrl, i - 1]
          );
        }
      }

      await client.query('COMMIT');

      // ── Restock notification ──────────────────────────────
      // If stock went from 0 → >0, notify subscribers via Telegram Bot API
      try {
        const oldStock = existingProduct?.available_stock ?? existingProduct?.stock ?? 0;
        const newStock = Number(stock) || 0;
        if (oldStock < 1 && newStock > 0) {
          const botToken = process.env.BOT_TOKEN;
          if (botToken) {
            const subs = await query<{ user_id: number }>(
              'SELECT user_id FROM restock_subscriptions WHERE product_id = $1 AND notified = false',
              [productId]
            );
            if (subs.length > 0) {
              const shopRow = await queryOne<{ name: string }>('SELECT name FROM shops WHERE id = $1', [owner.shop_id]);
              const shopName = shopRow?.name || '';
              const msg = `🔔 محصول دوباره موجود شد!\n\n🛍 ${name}\n💰 ${Number(price).toLocaleString()} تومان\n🏪 ${shopName}\n\nاکنون می‌تونی خرید کنی!`;
              const keyboard = JSON.stringify({ inline_keyboard: [[{ text: '🛒 مشاهده محصول', callback_data: `prod:open:${productId}:0:0` }]] });

              for (const sub of subs) {
                try {
                  await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ chat_id: sub.user_id, text: msg, reply_markup: keyboard }),
                  });
                } catch { /* ignore individual send failures */ }
              }

              // Mark as notified
              await query(
                'UPDATE restock_subscriptions SET notified = true WHERE product_id = $1 AND notified = false',
                [productId]
              );
            }
          }
        }
      } catch (notifyErr) {
        console.error('Restock notification error:', notifyErr);
      }

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
