import { NextRequest, NextResponse } from 'next/server';
import { requireSeller } from '@/lib/auth';
import { query, queryOne } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const session = await requireSeller();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Get shop_id
    const owner = await queryOne(
      'SELECT shop_id FROM shop_owners WHERE user_id = $1',
      [session.userId]
    );

    if (!owner) {
      return NextResponse.json({ error: 'Shop not found' }, { status: 404 });
    }

    const shopId = owner.shop_id;

    // 1. Total Revenue (from completed orders)
    const revenueResult = await queryOne(
      `SELECT COALESCE(SUM(total_price), 0) as total_revenue 
       FROM orders 
       WHERE shop_id = $1 AND status = 'completed'`,
      [shopId]
    );

    // 2. Total Orders Count
    const ordersCountResult = await queryOne(
      `SELECT COUNT(*) as count FROM orders WHERE shop_id = $1`,
      [shopId]
    );

    // 3. Sales Chart (Last 7 Days)
    const salesChart = await query(
      `SELECT 
         DATE(created_at) as date, 
         COUNT(*) as order_count, 
         COALESCE(SUM(total_price), 0) as daily_revenue
       FROM orders 
       WHERE shop_id = $1 AND created_at >= NOW() - INTERVAL '7 days'
       GROUP BY DATE(created_at)
       ORDER BY date ASC`,
      [shopId]
    );

    // 4. Top Selling Products
    const topProducts = await query(
      `SELECT 
         p.name, 
         SUM(oi.quantity) as total_sold,
         SUM(oi.quantity * oi.price) as product_revenue
       FROM order_items oi
       JOIN products p ON oi.product_id = p.id
       JOIN orders o ON oi.order_id = o.id
       WHERE o.shop_id = $1 AND o.status = 'completed'
       GROUP BY p.id, p.name
       ORDER BY total_sold DESC
       LIMIT 5`,
      [shopId]
    );

    // 5. Pending Orders Count
    const pendingCount = await queryOne(
      `SELECT COUNT(*) as count FROM orders WHERE shop_id = $1 AND status = 'pending'`,
      [shopId]
    );

    return NextResponse.json({
      totalRevenue: revenueResult?.total_revenue || 0,
      totalOrders: parseInt(ordersCountResult?.count || 0),
      pendingOrders: parseInt(pendingCount?.count || 0),
      salesChart,
      topProducts,
    });

  } catch (error) {
    console.error('Stats API error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
