// ─── Admin: Claim Codes ───
import { Key, Plus } from 'lucide-react';
import { getAllClaimCodes, getAllShops } from '@/lib/db';
import { toJalali } from '@/lib/utils';

export const dynamic = 'force-dynamic';

export default async function AdminClaimCodesPage() {
  const [codes, shops] = await Promise.all([getAllClaimCodes(), getAllShops()]);
  const shopMap = new Map(shops.map((s) => [s.id, s.name]));

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="flex items-center gap-2 text-2xl font-black">
          <Key className="h-6 w-6 text-[var(--primary)]" />
          کدهای دعوت
        </h1>
        <details className="relative">
          <summary className="flex cursor-pointer items-center gap-2 rounded-[var(--radius-lg)] bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[var(--primary-dark)] transition-all active:scale-[0.97] [&::-webkit-details-marker]:hidden">
            <Plus className="h-4 w-4" />
            ساخت کد جدید
          </summary>
          <form
            action="/api/admin/create-claim-code"
            method="POST"
            className="absolute left-0 top-full z-10 mt-2 w-72 rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white p-4 shadow-[var(--shadow-pop)]"
          >
            <select
              name="shop_id"
              className="mb-3 w-full rounded-[var(--radius)] border border-[var(--border)] bg-white px-3 py-2.5 text-sm outline-none transition focus:border-[var(--primary)]"
              required
            >
              <option value="">انتخاب فروشگاه...</option>
              {shops.map((shop) => (
                <option key={shop.id} value={shop.id}>{shop.name}</option>
              ))}
            </select>
            <button
              type="submit"
              className="w-full rounded-[var(--radius-lg)] bg-[var(--primary)] py-2.5 text-sm font-semibold text-white hover:bg-[var(--primary-dark)] transition-all active:scale-[0.97]"
            >
              ایجاد کد
            </button>
          </form>
        </details>
      </div>

      <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white shadow-[var(--shadow-card)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border-light)]">
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">کد</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">فروشگاه</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">استفاده شده</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">توسط</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">انقضا</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">تاریخ ساخت</th>
            </tr>
          </thead>
          <tbody>
            {codes.map((code) => (
              <tr key={code.id} className="border-b border-[var(--border-light)]/50 transition hover:bg-[var(--bg-muted)]">
                <td className="px-4 py-3 font-mono text-xs font-semibold">{code.code}</td>
                <td className="px-4 py-3 text-[var(--text-secondary)]">{shopMap.get(code.shop_id) || code.shop_id}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    code.is_used
                      ? 'bg-[var(--danger)]/10 text-[var(--danger)]'
                      : 'bg-[var(--success)]/10 text-[var(--success)]'
                  }`}>
                    {code.is_used ? 'بله' : 'خیر'}
                  </span>
                </td>
                <td className="px-4 py-3 text-[var(--text-tertiary)]">{code.used_by || '—'}</td>
                <td className="px-4 py-3 text-[var(--text-tertiary)]">{toJalali(code.expires_at)}</td>
                <td className="px-4 py-3 text-[var(--text-tertiary)]">{toJalali(code.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}