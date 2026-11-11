import { NextRequest, NextResponse } from 'next/server';
import { getProductById } from '@/lib/db';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

// SVG placeholder for missing images
const PLACEHOLDER_SVG = `
<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#e5e7eb"/>
  <circle cx="200" cy="120" r="30" fill="#9ca3af"/>
  <path d="M200 90c-16.5 0-30 13.5-30 30s13.5 30 30 30 30-13.5 30-30-13.5-30-30-30zm0 10c11 0 20 9 20 20s-9 20-20 20-20-9-20-20 9-20 20-20z" fill="#e5e7eb"/>
  <rect x="170" y="180" width="60" height="4" rx="2" fill="#9ca3af"/>
  <text x="200" y="220" text-anchor="middle" font-family="system-ui" font-size="14" fill="#9ca3af">تصویری یافت نشد</text>
</svg>
`.trim();

const PLACEHOLDER_SVG_BUFFER = Buffer.from(PLACEHOLDER_SVG);

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const product = await getProductById(parseInt(id)).catch(() => null);

  if (!product) {
    return new NextResponse(PLACEHOLDER_SVG_BUFFER, {
      headers: {
        'Content-Type': 'image/svg+xml',
        'Cache-Control': 'public, max-age=3600',
      },
    });
  }

  // 1. First try local storage (image_url — may be /uploads/... or /api/... or /data/...)
  if (product.image_url) {
    try {
      // Support both legacy /uploads/products/ and new /data/product_images/ paths
      let localPath = null;
      if (product.image_url.startsWith('/uploads/')) {
        localPath = path.join('/app', product.image_url);
      } else if (product.image_url.startsWith('/data/')) {
        localPath = path.join('/app', product.image_url);
      } else if (product.image_url.startsWith('/api/product-image-file/')) {
        const filename = product.image_url.split('/').pop();
        localPath = path.join('/app', 'data', 'product_images', filename);
      }
      if (localPath && fs.existsSync(localPath)) {
        const fileBuffer = fs.readFileSync(localPath);
        const ext = path.extname(localPath).toLowerCase();
        const contentType = ext === '.png' ? 'image/png' : 
                           ext === '.webp' ? 'image/webp' : 'image/jpeg';
        return new NextResponse(fileBuffer, {
          headers: {
            'Content-Type': contentType,
            'Cache-Control': 'public, max-age=31536000, immutable',
          },
        });
      }
    } catch (err) {
      console.error('Local image read error:', err);
    }
  }

  // 2. Fallback to Telegram file_id (for backward compatibility)
  //    Support ?extra=N for legacy additional images stored in product_images.file_id
  const url = new URL(request.url);
  const extraIndex = parseInt(url.searchParams.get('extra') || '', 10);

  let fileId = product.image_file_id;
  if (!Number.isNaN(extraIndex)) {
    const { query } = await import('@/lib/db');
    const rows = await query<{ file_id: string | null }>(
      'SELECT file_id FROM product_images WHERE product_id = $1 ORDER BY sort_order LIMIT 1 OFFSET $2',
      [product.id, extraIndex]
    ).catch(() => [] as { file_id: string | null }[]);
    fileId = rows?.[0]?.file_id || null;
  }

  if (fileId) {
    const botToken = process.env.BOT_TOKEN;
    if (botToken) {
      try {
        const fileInfoRes = await fetch(
          `https://api.telegram.org/bot${botToken}/getFile?file_id=${encodeURIComponent(fileId)}`
        );
        const fileInfo = await fileInfoRes.json();

        if (fileInfo.ok && fileInfo.result?.file_path) {
          const fileUrl = `https://api.telegram.org/file/bot${botToken}/${fileInfo.result.file_path}`;
          const imageRes = await fetch(fileUrl);
          
          if (imageRes.ok) {
            const arrayBuffer = await imageRes.arrayBuffer();
            const contentType = imageRes.headers.get('content-type') || 'image/jpeg';
            
            return new NextResponse(arrayBuffer, {
              headers: {
                'Content-Type': contentType,
                'Cache-Control': 'public, max-age=31536000, immutable',
              },
            });
          }
        }
      } catch (err) {
        console.error('Telegram image fetch error:', err);
      }
    }
  }

  // 3. Final fallback: placeholder
  return new NextResponse(PLACEHOLDER_SVG_BUFFER, {
    headers: {
      'Content-Type': 'image/svg+xml',
      'Cache-Control': 'public, max-age=3600',
    },
  });
}