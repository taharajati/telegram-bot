// src/lib/db.ts
// PostgreSQL connection via pg (Node.js native driver)
// Compatible with Turbopack, no WASM issues

import { Pool } from 'pg';
import type { QueryResult, QueryResultRow } from 'pg';

// Pool instance (singleton)
let _pool: Pool | null = null;

function getPool(): Pool {
  if (_pool) return _pool;
  
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error('DATABASE_URL environment variable is not set');
  }
  
  _pool = new Pool({
    connectionString: databaseUrl,
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
  });
  
  _pool.on('error', (err) => {
    console.error('Unexpected pg pool error:', err);
  });
  
  return _pool;
}

async function query<T = any>(sql: string, params: any[] = []): Promise<T[]> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    const result = await client.query(sql, params);
    return result.rows as T[];
  } finally {
    client.release();
  }
}

async function queryOne<T = any>(sql: string, params: any[] = []): Promise<T | null> {
  const rows = await query<T>(sql, params);
  return rows.length > 0 ? rows[0] : null;
}

async function exec(sql: string, params: any[] = []): Promise<void> {
  const pool = getPool();
  const client = await pool.connect();
  try {
    await client.query(sql, params);
  } finally {
    client.release();
  }
}

// ─── Shops ───────────────────────────────────────────────
export async function getActiveShops() {
  return query('SELECT * FROM shops WHERE is_active = true ORDER BY name');
}

export async function getAllShops() {
  return query('SELECT * FROM shops ORDER BY id DESC');
}

export async function getShopById(id: number) {
  return queryOne('SELECT * FROM shops WHERE id = $1', [id]);
}

export async function toggleShopActive(id: number) {
  const shop = await getShopById(id);
  if (!shop) return;
  await exec('UPDATE shops SET is_active = NOT is_active WHERE id = $1', [id]);
}

// ─── Categories ──────────────────────────────────────────
export async function getCategoriesByShop(shopId: number) {
  return query('SELECT * FROM categories WHERE shop_id = $1 ORDER BY name', [shopId]);
}

// ─── Products ────────────────────────────────────────────
export async function getActiveProducts(limit = 12) {
  return query('SELECT * FROM products WHERE is_active = true ORDER BY id DESC LIMIT $1', [limit]);
}

export async function getProductById(id: number) {
  return queryOne('SELECT * FROM products WHERE id = $1', [id]);
}

export async function getProductsByCategory(catId: number) {
  return query('SELECT * FROM products WHERE category_id = $1 AND is_active = true ORDER BY name', [catId]);
}

export async function getProductsByShop(shopId: number) {
  return query(
    'SELECT p.* FROM products p JOIN categories c ON p.category_id = c.id WHERE c.shop_id = $1 ORDER BY p.name',
    [shopId]
  );
}

export async function getAllProducts() {
  return query('SELECT * FROM products ORDER BY id DESC');
}

export async function toggleProductActive(productId: number) {
  const product = await getProductById(productId);
  if (!product) return;
  await exec('UPDATE products SET is_active = NOT is_active WHERE id = $1', [productId]);
}

export async function searchProducts(q: string) {
  return query('SELECT * FROM products WHERE is_active = true AND name ILIKE $1 ORDER BY name', [`%${q}%`]);
}

// ─── Orders ──────────────────────────────────────────────
export async function getOrdersByShop(shopId: number) {
  return query('SELECT * FROM orders WHERE shop_id = $1 ORDER BY id DESC', [shopId]);
}

export async function getAllOrders() {
  return query('SELECT * FROM orders ORDER BY id DESC');
}

export async function getOrderById(id: number) {
  return queryOne('SELECT * FROM orders WHERE id = $1', [id]);
}

export async function getOrderByTracking(trackingCode: string) {
  return queryOne('SELECT * FROM orders WHERE tracking_code = $1', [trackingCode]);
}

export async function getOrderItems(orderId: number) {
  return query('SELECT * FROM order_items WHERE order_id = $1', [orderId]);
}

export async function updateOrderStatus(orderId: number, status: string, by = 'web') {
  const order = await getOrderById(orderId);
  if (!order) return;
  const history = order.status_history ? JSON.parse(order.status_history) : [];
  history.push({ status, by, at: new Date().toISOString() });
  await exec(
    'UPDATE orders SET status = $1, status_history = $2, updated_at = NOW() WHERE id = $3',
    [status, JSON.stringify(history), orderId]
  );
}

// ─── Users ───────────────────────────────────────────────
export async function getAllUsers() {
  return query('SELECT * FROM users ORDER BY user_id DESC');
}

export async function toggleUserBlocked(userId: number) {
  const user = await queryOne('SELECT * FROM users WHERE user_id = $1', [userId]);
  if (!user) return;
  await exec('UPDATE users SET is_blocked = NOT is_blocked WHERE user_id = $1', [userId]);
}

export async function getUserById(userId: number) {
  return queryOne('SELECT * FROM users WHERE user_id = $1', [userId]);
}

// ─── Shop Owners (Sellers) ──────────────────────────────
export async function getShopOwner(userId: number) {
  const row = await queryOne<{
    id: number;
    user_id: number;
    shop_id: number;
    first_name: string | null;
    username: string | null;
    password_hash: string | null;
    password_salt: string | null;
    registered_at: Date;
  }>('SELECT * FROM shop_owners WHERE user_id = $1', [userId]);
  return row;
}

export async function setSellerPassword(userId: number, passwordHash: string, passwordSalt: string) {
  await exec(
    'UPDATE shop_owners SET password_hash = $1, password_salt = $2, must_change_password = false WHERE user_id = $3',
    [passwordHash, passwordSalt, userId]
  );
}

export async function getShopByOwner(userId: number) {
  return queryOne(
    'SELECT s.* FROM shops s JOIN shop_owners so ON s.id = so.shop_id WHERE so.user_id = $1',
    [userId]
  );
}

// ─── Admins ────────────────────────────────────────────────
export async function getAdminByUserId(userId: number) {
  const row = await queryOne<{
    id: number;
    user_id: number;
    password_hash: string;
    created_at: Date;
  }>('SELECT * FROM admins WHERE user_id = $1', [userId]);
  return row;
}

export async function setAdminPassword(userId: number, passwordHash: string) {
  await exec(
    'INSERT INTO admins (user_id, password_hash, must_change_password) VALUES ($1, $2, false) ON CONFLICT (user_id) DO UPDATE SET password_hash = $2, must_change_password = false',
    [userId, passwordHash]
  );
}

// ─── Claim Codes ─────────────────────────────────────────
export async function getAllClaimCodes() {
  return query('SELECT * FROM claim_codes ORDER BY id DESC');
}

export async function createClaimCode(shopId: number, createdBy: number, expiresAt: Date) {
  const code = Math.random().toString(36).substring(2, 10).toUpperCase();
  await exec(
    'INSERT INTO claim_codes (code, shop_id, created_by, expires_at) VALUES ($1, $2, $3, $4)',
    [code, shopId, createdBy, expiresAt]
  );
  return code;
}

// ─── Recent Activity (for landing ticker) ────────────────
export async function getRecentActivity(limit = 10) {
  const recentOrders = await query<{
    id: number; tracking_code: string; status: string; payment_status: string;
    total_price: number; shop_id: number; created_at: Date;
  }>(`SELECT id, tracking_code, status, payment_status, total_price, shop_id, created_at
     FROM orders ORDER BY created_at DESC LIMIT $1`, [limit]);
  return recentOrders.map(o => ({
    type: 'order' as const,
    label: o.status === 'paid' ? 'پرداخت کارت‌به‌کارت' :
           o.status === 'pending_payment' && o.payment_status === 'pending' ? 'سفارش جدید' :
           o.status === 'delivered' ? 'تحویل شده' : 'سفارش',
    shop_id: o.shop_id,
    created_at: o.created_at,
  }));
}

export async function getRecentActiveShops(limit = 5) {
  return query<{ id: number; name: string; created_at: Date }>(
    'SELECT id, name, created_at FROM shops WHERE is_active = true ORDER BY created_at DESC LIMIT $1',
    [limit]
  );
}

// ─── Stats ───────────────────────────────────────────────
export async function getStats() {
  const [totalShops, activeShops, totalProducts, totalOrders, pendingOrders, paidOrders, totalUsers] = await Promise.all([
    queryOne('SELECT COUNT(*) as c FROM shops'),
    queryOne('SELECT COUNT(*) as c FROM shops WHERE is_active = true'),
    queryOne('SELECT COUNT(*) as c FROM products'),
    queryOne('SELECT COUNT(*) as c FROM orders'),
    queryOne("SELECT COUNT(*) as c FROM orders WHERE status IN ('pending_payment','pending')"),
    queryOne("SELECT COUNT(*) as c FROM orders WHERE payment_status = 'paid'"),
    queryOne('SELECT COUNT(*) as c FROM users'),
  ]);
  return {
    totalShops: totalShops?.c || 0,
    activeShops: activeShops?.c || 0,
    totalProducts: totalProducts?.c || 0,
    totalOrders: totalOrders?.c || 0,
    pendingOrders: pendingOrders?.c || 0,
    paidOrders: paidOrders?.c || 0,
    totalUsers: totalUsers?.c || 0,
  };
}

export async function getShopStats(shopId: number) {
  const [totalProducts, totalOrders, pendingOrders, paidOrders, totalRevenue] = await Promise.all([
    queryOne(
      'SELECT COUNT(*) as c FROM products p JOIN categories c ON p.category_id = c.id WHERE c.shop_id = $1',
      [shopId]
    ),
    queryOne('SELECT COUNT(*) as c FROM orders WHERE shop_id = $1', [shopId]),
    queryOne("SELECT COUNT(*) as c FROM orders WHERE shop_id = $1 AND status IN ('pending_payment','pending')", [shopId]),
    queryOne("SELECT COUNT(*) as c FROM orders WHERE shop_id = $1 AND payment_status = 'paid'", [shopId]),
    queryOne("SELECT COALESCE(SUM(total_price),0) as c FROM orders WHERE shop_id = $1 AND payment_status = 'paid'", [shopId]),
  ]);
  return {
    totalProducts: totalProducts?.c || 0,
    totalOrders: totalOrders?.c || 0,
    pendingOrders: pendingOrders?.c || 0,
    paidOrders: paidOrders?.c || 0,
    totalRevenue: totalRevenue?.c || 0,
  };
}

// ─── Site Content (Dynamic) ──────────────────────────────
export interface SiteContentItem {
  id: number;
  section: string;
  key: string;
  value: string;
  locale: string;
  updated_at: Date;
}

export async function getSiteContent(section: string, locale = 'fa'): Promise<Record<string, string>> {
  const rows = await query<SiteContentItem>(
    'SELECT key, value FROM site_content WHERE section = $1 AND locale = $2',
    [section, locale]
  );
  return Object.fromEntries(rows.map(r => [r.key, r.value]));
}

export async function getAllSiteContent(locale = 'fa'): Promise<Record<string, Record<string, string>>> {
  const rows = await query<SiteContentItem>(
    'SELECT section, key, value FROM site_content WHERE locale = $1',
    [locale]
  );
  const result: Record<string, Record<string, string>> = {};
  for (const row of rows) {
    if (!result[row.section]) result[row.section] = {};
    result[row.section][row.key] = row.value;
  }
  return result;
}

export async function updateSiteContent(section: string, key: string, value: string, locale = 'fa') {
  await exec(
    `INSERT INTO site_content (section, key, value, locale) VALUES ($1, $2, $3, $4)
     ON CONFLICT (section, key, locale) DO UPDATE SET value = $3, updated_at = NOW()`,
    [section, key, value, locale]
  );
}

// ─── Insert Order ────────────────────────────────────────
export async function insertOrder(data: {
  shop_id: number;
  user_id: number;
  tracking_code: string;
  total_price: number;
  receiver_name?: string;
  shipping_address?: string;
  phone?: string;
  status?: string;
  payment_method?: string;
  payment_status?: string;
}) {
  const result = await queryOne<{ id: number }>(
    `INSERT INTO orders (shop_id, user_id, tracking_code, total_price, receiver_name, shipping_address, phone, status, payment_method, payment_status)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING id`,
    [
      data.shop_id, data.user_id, data.tracking_code, data.total_price,
      data.receiver_name || null, data.shipping_address || null, data.phone || null,
      data.status || 'pending', data.payment_method || null, data.payment_status || 'pending',
    ]
  );
  return result?.id;
}

// Close pool on shutdown (useful for tests)
export async function closePool() {
  if (_pool) {
    await _pool.end();
    _pool = null;
  }
}