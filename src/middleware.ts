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
  if (!token) return NextResponse.redirect(new URL('/login', req.url));

  try {
    const { payload } = await jwtVerify(token, SECRET);
    const role = payload.role as string;
    const path = req.nextUrl.pathname;

    if (path.startsWith('/admin') && role !== 'admin') {
      return NextResponse.redirect(new URL('/login', req.url));
    }
    if (path.startsWith('/seller') && role !== 'seller' && role !== 'admin') {
      return NextResponse.redirect(new URL('/login', req.url));
    }
    return NextResponse.next();
  } catch {
    return NextResponse.redirect(new URL('/login', req.url));
  }
}
