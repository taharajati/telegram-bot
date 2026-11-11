"use client";

import { useState, useEffect } from 'react';
import { TrendingUp, ShoppingBag, DollarSign, Clock, Loader2 } from 'lucide-react';
import Card from '@/components/shared/Card';
import { formatPrice } from '@/lib/utils';

interface StatsData {
  totalRevenue: number;
  totalOrders: number;
  pendingOrders: number;
  salesChart: Array<{date: string, order_count: string, daily_revenue: string}>;
  topProducts: Array<{name: string, total_sold: string, product_revenue: string}>;
}

export default function SellerStatsPage() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/seller/stats')
      .then(res => res.json())
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load stats:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="animate-spin text-[var(--primary)]" size={40} />
      </div>
    );
  }

  if (!stats) return <div>خطا در دریافت اطلاعات</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-black">📊 آمار و گزارش‌ها</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-100 rounded-full text-green-600">
              <DollarSign size={24} />
            </div>
            <div>
              <p className="text-sm text-[var(--text-tertiary)]">درآمد کل</p>
              <p className="text-xl font-bold text-[var(--primary)]">{formatPrice(stats.totalRevenue)}</p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 rounded-full text-blue-600">
              <ShoppingBag size={24} />
            </div>
            <div>
              <p className="text-sm text-[var(--text-tertiary)]">تعداد سفارشات</p>
              <p className="text-xl font-bold">{stats.totalOrders}</p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-orange-100 rounded-full text-orange-600">
              <Clock size={24} />
            </div>
            <div>
              <p className="text-sm text-[var(--text-tertiary)]">در انتظار بررسی</p>
              <p className="text-xl font-bold">{stats.pendingOrders}</p>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sales Chart */}
        <Card className="p-6">
          <h3 className="mb-4 font-bold flex items-center gap-2">
            <TrendingUp size={20} />
            نمودار فروش ۷ روز گذشته
          </h3>
          <div className="h-64 flex items-end gap-2">
            {stats.salesChart.map((day, idx) => {
              const maxRev = Math.max(...stats.salesChart.map(d => parseFloat(d.daily_revenue)), 1);
              const height = (parseFloat(day.daily_revenue) / maxRev) * 100;
              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-2 group">
                  <div className="relative w-full bg-gray-100 rounded-t-md overflow-hidden" style={{height: '200px'}}>
                    <div 
                      className="absolute bottom-0 w-full bg-[var(--primary)] transition-all duration-500 group-hover:bg-[var(--primary-dark)]"
                      style={{height: `${height}%`}}
                    />
                  </div>
                  <span className="text-xs text-[var(--text-tertiary)]">
                    {new Date(day.date).toLocaleDateString('fa-IR', {month: 'short', day: 'numeric'})}
                  </span>
                </div>
              );
            })}
            {stats.salesChart.length === 0 && (
              <div className="w-full h-full flex items-center justify-center text-[var(--text-tertiary)]">
                داده‌ای برای نمایش وجود ندارد
              </div>
            )}
          </div>
        </Card>

        {/* Top Products */}
        <Card className="p-6">
          <h3 className="mb-4 font-bold flex items-center gap-2">
            <TrendingUp size={20} className="rotate-90" />
            پرفروش‌ترین محصولات
          </h3>
          <div className="space-y-4">
            {stats.topProducts.map((product, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-[var(--bg-muted)] rounded-[var(--radius)]">
                <div>
                  <p className="font-semibold text-sm">{product.name}</p>
                  <p className="text-xs text-[var(--text-tertiary)]">{product.total_sold} عدد فروش رفته</p>
                </div>
                <span className="font-bold text-[var(--primary)] text-sm">
                  {formatPrice(parseFloat(product.product_revenue))}
                </span>
              </div>
            ))}
            {stats.topProducts.length === 0 && (
              <div className="text-center text-[var(--text-tertiary)] py-8">
                هنوز فروشی ثبت نشده است
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
