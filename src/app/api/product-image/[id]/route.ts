import { NextRequest, NextResponse } from 'next/server';
import { getProductById } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const product = await getProductById(parseInt(id)).catch(() => null);

  if (!product || !product.image_file_id) {
    // Return 1x1 transparent PNG
    const pixel = Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
      'base64'
    );
    return new NextResponse(pixel, {
      headers: {
        'Content-Type': 'image/png',
        'Cache-Control': 'public, max-age=31536000, immutable',
      },
    });
  }

  const botToken = process.env.BOT_TOKEN;
  if (!botToken) {
    return new NextResponse('Bot token not configured', { status: 500 });
  }

  try {
    // Get file path from Telegram
    const fileInfoRes = await fetch(
      `https://api.telegram.org/bot${botToken}/getFile?file_id=${encodeURIComponent(product.image_file_id)}`
    );
    const fileInfo = await fileInfoRes.json();

    if (!fileInfo.ok || !fileInfo.result?.file_path) {
      throw new Error('File not found in Telegram');
    }

    // Stream the file from Telegram
    const fileUrl = `https://api.telegram.org/file/bot${botToken}/${fileInfo.result.file_path}`;
    const imageRes = await fetch(fileUrl);

    if (!imageRes.ok) {
      throw new Error('Failed to fetch image from Telegram');
    }

    const arrayBuffer = await imageRes.arrayBuffer();
    const contentType = imageRes.headers.get('content-type') || 'image/jpeg';

    return new NextResponse(arrayBuffer, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=31536000, immutable',
      },
    });
  } catch {
    // Fallback transparent pixel
    const pixel = Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
      'base64'
    );
    return new NextResponse(pixel, {
      headers: {
        'Content-Type': 'image/png',
        'Cache-Control': 'public, max-age=31536000, immutable',
      },
    });
  }
}