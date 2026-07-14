// src/app/api/auth/me/route.ts
import { NextResponse } from 'next/server';
import { getSession } from '@/lib/auth';

export async function GET() {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ authenticated: false });
  }
  return NextResponse.json({
    authenticated: true,
    userId: session.userId,
    role: session.role,
    shopId: session.shopId,
    firstName: session.firstName,
  });
}