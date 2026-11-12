// src/lib/panel.ts — بافت مشترک صفحات پنل (یک‌بار در هر درخواست)
import { cache } from 'react';
import { redirect } from 'next/navigation';
import { requireAdmin, requireSeller } from '@/lib/auth';
import { getShopById, getShopOwner } from '@/lib/db';

export const getSellerContext = cache(async () => {
  const session = await requireSeller().catch(() => redirect('/login'));
  const owner = await getShopOwner(session.userId);
  if (!owner) redirect('/login');
  const shop = await getShopById(owner.shop_id);
  if (!shop) redirect('/login');
  return { session, owner, shop };
});

export const getAdminContext = cache(async () => {
  const session = await requireAdmin().catch(() => redirect('/login'));
  return { session };
});

/** پارامتر صفحه‌ی ?page= را به عدد معتبر تبدیل می‌کند. */
export function parsePage(value: string | undefined): number {
  const n = value && /^\d+$/.test(value) ? parseInt(value, 10) : 1;
  return n >= 1 ? n : 1;
}
