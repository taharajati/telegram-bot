// src/lib/queries.ts
// کوئری‌های صفحات عمومی و پنل‌ها. اتصال و کوئری‌های پایه در db.ts هستند.
import { query, queryOne } from '@/lib/db';

// ─── Public storefront ───────────────────────────────────
const PUBLIC_SHOP = "s.is_active = true AND s.status = 'active'";

export interface PublicShop {
  id: number;
  name: string;
  description: string | null;
  product_count: number;
}

export async function getPublicShops(opts: { q?: string; limit?: number } = {}): Promise<PublicShop[]> {
  const params: unknown[] = [];
  let where = PUBLIC_SHOP;
  if (opts.q) {
    params.push(`%${opts.q}%`);
    where += ` AND s.name ILIKE $${params.length}`;
  }
  params.push(opts.limit ?? 24);
  return query<PublicShop>(
    `SELECT s.id, s.name, s.description,
            COUNT(p.id) FILTER (WHERE p.is_active)::int AS product_count
       FROM shops s LEFT JOIN products p ON p.shop_id = s.id
      WHERE ${where}
      GROUP BY s.id
      ORDER BY product_count DESC, s.id DESC
      LIMIT $${params.length}`,
    params
  );
}

export async function getPublicShop(id: number) {
  return queryOne(`SELECT s.* FROM shops s WHERE s.id = $1 AND ${PUBLIC_SHOP}`, [id]);
}

export interface PublicProduct {
  id: number;
  shop_id: number;
  name: string;
  price: number | string;
  stock: number;
  reserved_stock: number;
  image_url: string | null;
  image_file_id: string | null;
  category_id: number | null;
  category_name: string | null;
  shop_name: string;
}

export async function getPublicProducts(
  opts: { shopId?: number; categoryId?: number; q?: string; limit?: number } = {}
): Promise<PublicProduct[]> {
  const params: unknown[] = [];
  let where = `p.is_active = true AND ${PUBLIC_SHOP}`;
  if (opts.shopId) {
    params.push(opts.shopId);
    where += ` AND p.shop_id = $${params.length}`;
  }
  if (opts.categoryId) {
    params.push(opts.categoryId);
    where += ` AND p.category_id = $${params.length}`;
  }
  if (opts.q) {
    params.push(`%${opts.q}%`);
    where += ` AND p.name ILIKE $${params.length}`;
  }
  params.push(opts.limit ?? 48);
  return query<PublicProduct>(
    `SELECT p.id, p.shop_id, p.name, p.price, p.stock, p.reserved_stock, p.image_url, p.image_file_id,
            p.category_id, c.name AS category_name, s.name AS shop_name
       FROM products p
       JOIN shops s ON s.id = p.shop_id
       LEFT JOIN categories c ON c.id = p.category_id
      WHERE ${where}
      ORDER BY p.id DESC
      LIMIT $${params.length}`,
    params
  );
}

export async function getPublicProduct(id: number) {
  return queryOne(
    `SELECT p.*, c.name AS category_name
       FROM products p
       JOIN shops s ON s.id = p.shop_id
       LEFT JOIN categories c ON c.id = p.category_id
      WHERE p.id = $1 AND p.is_active = true AND ${PUBLIC_SHOP}`,
    [id]
  );
}

export async function getActivePlans() {
  return query<{ id: number; name: string; duration_days: number; price: number | string }>(
    'SELECT id, name, duration_days, price FROM subscription_plans WHERE is_active = true ORDER BY duration_days'
  );
}

// ─── Orders (paginated, filtered in SQL) ─────────────────
export async function getOrdersPage(opts: { shopId?: number; status?: string; page?: number; pageSize?: number }) {
  const pageSize = opts.pageSize ?? 20;
  const page = Math.max(1, Math.floor(opts.page ?? 1));
  const params: unknown[] = [];
  const conds: string[] = [];
  if (opts.shopId) {
    params.push(opts.shopId);
    conds.push(`shop_id = $${params.length}`);
  }
  if (opts.status) {
    params.push(opts.status);
    conds.push(`status = $${params.length}`);
  }
  const where = conds.length ? `WHERE ${conds.join(' AND ')}` : '';
  const totalRow = await queryOne<{ c: number }>(`SELECT COUNT(*)::int AS c FROM orders ${where}`, params);
  const rows = await query(
    `SELECT * FROM orders ${where} ORDER BY id DESC LIMIT ${pageSize} OFFSET ${(page - 1) * pageSize}`,
    params
  );
  const total = totalRow?.c ?? 0;
  return { rows, total, page, pageSize, pageCount: Math.max(1, Math.ceil(total / pageSize)) };
}

export interface HistoryEntry {
  status: string;
  by: string;
  at: string | Date;
  description?: string | null;
}

/** تاریخچه از جدول order_history؛ اگر خالی بود از JSON قدیمی. */
export async function getOrderHistoryEntries(orderId: number, legacyJson?: string | null): Promise<HistoryEntry[]> {
  const rows = await query<{ status: string; changed_by: string; changed_at: Date; description: string | null }>(
    'SELECT status, changed_by, changed_at, description FROM order_history WHERE order_id = $1 ORDER BY changed_at, id',
    [orderId]
  ).catch(() => []);
  if (rows.length > 0) {
    return rows.map((r) => ({ status: r.status, by: r.changed_by, at: r.changed_at, description: r.description }));
  }
  try {
    const legacy = legacyJson ? JSON.parse(legacyJson) : [];
    return Array.isArray(legacy)
      ? legacy.map((e: { status: string; by: string; at: string }) => ({ status: e.status, by: e.by, at: e.at }))
      : [];
  } catch {
    return [];
  }
}

// ─── Seller overview (فروش فقط از سفارش‌های پرداخت‌شده و لغونشده) ──
const TEHRAN_DAY = "(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tehran')::date";
const TEHRAN_TODAY = "(NOW() AT TIME ZONE 'Asia/Tehran')::date";
const IS_PAID = "payment_status = 'paid' AND status NOT IN ('cancelled','refunded')";

export interface SellerOverview {
  revenueToday: number;
  revenue7d: number;
  revenue30d: number;
  revenueTotal: number;
  paidOrders: number;
  totalOrders: number;
  awaitingPayment: number;
  awaitingReview: number;
  toShip: number;
  products: number;
  lowStock: number;
  chart: { day: string; revenue: number; orders: number }[];
  topProducts: { name: string; sold: number; revenue: number }[];
}

function tehranDays(n: number): string[] {
  const fmt = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Tehran' });
  const out: string[] = [];
  for (let i = n - 1; i >= 0; i--) out.push(fmt.format(new Date(Date.now() - i * 86400000)));
  return out;
}

export async function getSellerOverview(shopId: number): Promise<SellerOverview> {
  const [agg, chartRows, top, prod] = await Promise.all([
    queryOne<Record<string, string>>(
      `SELECT
         COALESCE(SUM(total_price) FILTER (WHERE ${IS_PAID} AND ${TEHRAN_DAY} = ${TEHRAN_TODAY}), 0) AS revenue_today,
         COALESCE(SUM(total_price) FILTER (WHERE ${IS_PAID} AND ${TEHRAN_DAY} >= ${TEHRAN_TODAY} - 6), 0) AS revenue_7d,
         COALESCE(SUM(total_price) FILTER (WHERE ${IS_PAID} AND ${TEHRAN_DAY} >= ${TEHRAN_TODAY} - 29), 0) AS revenue_30d,
         COALESCE(SUM(total_price) FILTER (WHERE ${IS_PAID}), 0) AS revenue_total,
         COUNT(*) FILTER (WHERE ${IS_PAID}) AS paid_orders,
         COUNT(*) AS total_orders,
         COUNT(*) FILTER (WHERE status = 'pending_payment' AND COALESCE(payment_status,'pending') <> 'pending_review') AS awaiting_payment,
         COUNT(*) FILTER (WHERE payment_status = 'pending_review' AND status NOT IN ('cancelled','refunded')) AS awaiting_review,
         COUNT(*) FILTER (WHERE status IN ('paid','confirmed')) AS to_ship
       FROM orders WHERE shop_id = $1`,
      [shopId]
    ),
    query<{ day: string; revenue: string; orders: string }>(
      `SELECT to_char(${TEHRAN_DAY}, 'YYYY-MM-DD') AS day,
              COALESCE(SUM(total_price), 0) AS revenue, COUNT(*) AS orders
         FROM orders
        WHERE shop_id = $1 AND ${IS_PAID} AND ${TEHRAN_DAY} >= ${TEHRAN_TODAY} - 6
        GROUP BY 1`,
      [shopId]
    ),
    query<{ name: string; sold: string; revenue: string }>(
      `SELECT oi.product_name AS name, SUM(oi.quantity) AS sold, SUM(oi.quantity * oi.unit_price) AS revenue
         FROM order_items oi JOIN orders o ON o.id = oi.order_id
        WHERE o.shop_id = $1 AND o.payment_status = 'paid' AND o.status NOT IN ('cancelled','refunded')
        GROUP BY oi.product_name ORDER BY sold DESC LIMIT 5`,
      [shopId]
    ),
    queryOne<{ products: string; low_stock: string }>(
      `SELECT COUNT(*) AS products,
              COUNT(*) FILTER (WHERE is_active AND stock - reserved_stock < 5) AS low_stock
         FROM products WHERE shop_id = $1`,
      [shopId]
    ),
  ]);
  const byDay = new Map(chartRows.map((r) => [r.day, r]));
  return {
    revenueToday: Number(agg?.revenue_today ?? 0),
    revenue7d: Number(agg?.revenue_7d ?? 0),
    revenue30d: Number(agg?.revenue_30d ?? 0),
    revenueTotal: Number(agg?.revenue_total ?? 0),
    paidOrders: Number(agg?.paid_orders ?? 0),
    totalOrders: Number(agg?.total_orders ?? 0),
    awaitingPayment: Number(agg?.awaiting_payment ?? 0),
    awaitingReview: Number(agg?.awaiting_review ?? 0),
    toShip: Number(agg?.to_ship ?? 0),
    products: Number(prod?.products ?? 0),
    lowStock: Number(prod?.low_stock ?? 0),
    chart: tehranDays(7).map((day) => ({
      day,
      revenue: Number(byDay.get(day)?.revenue ?? 0),
      orders: Number(byDay.get(day)?.orders ?? 0),
    })),
    topProducts: top.map((t) => ({ name: t.name, sold: Number(t.sold), revenue: Number(t.revenue) })),
  };
}

export async function getShopSubscription(shopId: number) {
  return queryOne<{
    end_date: Date;
    is_trial: boolean;
    approval_status: string;
    plan_name: string | null;
  }>(
    `SELECT ss.end_date, ss.is_trial, ss.approval_status, sp.name AS plan_name
       FROM shop_subscriptions ss LEFT JOIN subscription_plans sp ON sp.id = ss.plan_id
      WHERE ss.shop_id = $1 AND ss.superseded_at IS NULL
      ORDER BY ss.id DESC LIMIT 1`,
    [shopId]
  );
}

export async function getDiscountCodesByShop(shopId: number) {
  return query<{
    id: number;
    code: string;
    discount_type: string;
    discount_value: number | string;
    min_order_amount: number | string;
    max_uses: number;
    used_count: number;
    is_active: boolean;
    expires_at: Date | null;
  }>('SELECT * FROM discount_codes WHERE shop_id = $1 ORDER BY id DESC', [shopId]);
}

// ─── Admin ───────────────────────────────────────────────
export async function getAdminOverview() {
  const row = await queryOne<Record<string, string>>(
    `SELECT
       (SELECT COALESCE(SUM(total_price),0) FROM orders WHERE ${IS_PAID}) AS revenue_total,
       (SELECT COUNT(*) FROM orders WHERE payment_status = 'pending_review' AND status NOT IN ('cancelled','refunded')) AS awaiting_review,
       (SELECT COUNT(*) FROM shops WHERE status = 'draft') AS draft_shops`
  );
  return {
    revenueTotal: Number(row?.revenue_total ?? 0),
    awaitingReview: Number(row?.awaiting_review ?? 0),
    draftShops: Number(row?.draft_shops ?? 0),
  };
}

export interface AdminShopRow {
  id: number;
  name: string;
  description: string | null;
  status: string;
  is_active: boolean;
  created_at: Date;
  owner_username: string | null;
  owner_user_id: number | null;
  product_count: number;
  order_count: number;
  sub_end: Date | null;
  sub_trial: boolean | null;
}

export async function getAdminShops() {
  return query<AdminShopRow>(
    `SELECT s.id, s.name, s.description, s.status, s.is_active, s.created_at,
            so.username AS owner_username, so.user_id AS owner_user_id,
            (SELECT COUNT(*)::int FROM products p WHERE p.shop_id = s.id) AS product_count,
            (SELECT COUNT(*)::int FROM orders o WHERE o.shop_id = s.id) AS order_count,
            sub.end_date AS sub_end, sub.is_trial AS sub_trial
       FROM shops s
       LEFT JOIN LATERAL (SELECT username, user_id FROM shop_owners WHERE shop_id = s.id ORDER BY id LIMIT 1) so ON true
       LEFT JOIN LATERAL (
         SELECT end_date, is_trial FROM shop_subscriptions
          WHERE shop_id = s.id AND superseded_at IS NULL AND approval_status = 'approved'
          ORDER BY id DESC LIMIT 1) sub ON true
      ORDER BY s.id DESC`
  );
}

export interface AdminSubscriptionRow {
  id: number;
  shop_id: number;
  shop_name: string;
  is_trial: boolean;
  approval_status: string;
  start_date: Date;
  end_date: Date;
  created_at: Date;
  plan_name: string | null;
  price: number | string | null;
}

export async function getAdminSubscriptions() {
  return query<AdminSubscriptionRow>(
    `SELECT ss.id, ss.shop_id, s.name AS shop_name, ss.is_trial, ss.approval_status,
            ss.start_date, ss.end_date, ss.created_at, sp.name AS plan_name, sp.price
       FROM shop_subscriptions ss
       JOIN shops s ON s.id = ss.shop_id
       LEFT JOIN subscription_plans sp ON sp.id = ss.plan_id
      WHERE ss.superseded_at IS NULL
      ORDER BY (ss.approval_status = 'pending') DESC, ss.id DESC
      LIMIT 100`
  );
}
