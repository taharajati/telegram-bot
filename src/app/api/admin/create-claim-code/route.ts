// src/app/api/admin/create-claim-code/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const shopId = parseInt(formData.get('shop_id') as string);
    if (!shopId) return NextResponse.json({ error: 'Invalid' }, { status: 400 });

    const crypto = require('crypto');
    const code = crypto.randomBytes(5).toString('hex').toUpperCase();

    const db = require('@/lib/db');
    const { getDb } = db;

    const stmt = getDb().prepare(
      'INSERT INTO claim_codes (code, shop_id, created_by, is_used, expires_at, created_at) VALUES (?, ?, 0, 0, ?, ?)'
    );
    const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
    const now = new Date().toISOString();
    stmt.run(code, shopId, expiresAt, now);

    return NextResponse.redirect(new URL('/admin/claim-codes', request.url));
  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: 'Server error' }, { status: 500 });
  }
}
