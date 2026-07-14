// src/middleware.ts — محافظت مسیرهای /admin/* و /seller/*
// Edge Runtime (runs on Vercel Edge / Cloudflare Workers)
import { NextRequest, NextResponse } from 'next/server';
import { jwtVerify } from 'jose';

const SECRET = new TextEncoder().encode(process.env.JWT_SECRET || 'foroshgram_default_secret_change_me');
const COOKIE = 'fsh_session';

export const config = {
  matcher: ['/admin/:path*', '/seller/:path*'],
};

export async function middleware(req: NextRequest) {
  const token = req.cookies.get(COOKIE)?.value;
  if (!token) {
    const loginUrl = new URL('/login', req.url);
    // Force HTTPS when behind Cloudflare proxy
    if (req.headers.get('x-forwarded-proto') === 'https') {
      loginUrl.protocol = 'https:';
    }
    return NextResponse.redirect(loginUrl);
  }

  try {
    const { payload } = await jwtVerify(token, SECRET);
    const role = payload.role as string;
    const path = req.nextUrl.pathname;

    if (path.startsWith('/admin') && role !== 'admin') {
      const loginUrl = new URL('/login', req.url);
      if (req.headers.get('x-forwarded-proto') === 'https') loginUrl.protocol = 'https:';
      return NextResponse.redirect(loginUrl);
    }
    if (path.startsWith('/seller') && role !== 'seller' && role !== 'admin') {
      const loginUrl = new URL('/login', req.url);
      if (req.headers.get('x-forwarded-proto') === 'https') loginUrl.protocol = 'https:';
      return NextResponse.redirect(loginUrl);
    }
    return NextResponse.next();
  } catch {
    const loginUrl = new URL('/login', req.url);
    if (req.headers.get('x-forwarded-proto') === 'https') loginUrl.protocol = 'https:';
    return NextResponse.redirect(loginUrl);
  }
}
