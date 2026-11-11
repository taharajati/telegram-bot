import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

// Serve product image files from the mounted persistent directory.
// Files live in /app/data/product_images (host: /opt/foroshgram/data/product_images),
// which survives rebuilds — unlike public/uploads which is baked into the image.
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ filename: string }> }
) {
  const { filename } = await params;

  // Security: only allow safe filename characters
  if (!/^[a-zA-Z0-9-_]+(\.[a-zA-Z0-9]+)?$/.test(filename)) {
    return new NextResponse('Invalid filename', { status: 400 });
  }

  const filePath = path.join(process.cwd(), 'data', 'product_images', filename);

  try {
    if (!fs.existsSync(filePath)) {
      return new NextResponse('Not found', { status: 404 });
    }

    const fileBuffer = fs.readFileSync(filePath);
    const ext = path.extname(filePath).toLowerCase();
    const contentType =
      ext === '.png' ? 'image/png' :
      ext === '.webp' ? 'image/webp' :
      ext === '.gif' ? 'image/gif' : 'image/jpeg';

    return new NextResponse(fileBuffer, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=31536000, immutable',
      },
    });
  } catch (err) {
    console.error('Product image file read error:', err);
    return new NextResponse('Not found', { status: 404 });
  }
}
