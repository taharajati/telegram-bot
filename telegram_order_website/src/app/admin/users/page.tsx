// ─── Admin: Users ───
import { Users, Ban, Check } from 'lucide-react';
import { getAllUsers } from '@/lib/db';
import { toJalali } from '@/lib/utils';

export const dynamic = 'force-dynamic';

export default async function AdminUsersPage() {
  const users = await getAllUsers();

  return (
    <div>
      <h1 className="mb-6 text-2xl font-black">کاربران ({users.length})</h1>

      <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-[var(--border-light)] bg-white shadow-[var(--shadow-card)]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border-light)]">
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">شناسه</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">نام</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">نام کاربری</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">تلفن</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">مسدود</th>
              <th className="px-4 py-3 text-right font-semibold text-[var(--text-tertiary)]">تاریخ</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.user_id} className="border-b border-[var(--border-light)]/50 transition hover:bg-[var(--bg-muted)]">
                <td className="px-4 py-3 text-[var(--text-tertiary)]">{user.user_id}</td>
                <td className="px-4 py-3 font-semibold">{user.first_name || '—'}</td>
                <td className="px-4 py-3 text-[var(--text-secondary)]">@{user.username || '—'}</td>
                <td className="px-4 py-3 text-[var(--text-secondary)]" dir="ltr">{user.phone || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                    user.is_blocked
                      ? 'bg-[var(--danger)]/10 text-[var(--danger)]'
                      : 'bg-[var(--success)]/10 text-[var(--success)]'
                  }`}>
                    {user.is_blocked ? <Ban className="h-3 w-3" /> : <Check className="h-3 w-3" />}
                    {user.is_blocked ? 'بله' : 'خیر'}
                  </span>
                </td>
                <td className="px-4 py-3 text-[var(--text-tertiary)]">{toJalali(user.registered_at)}</td>
                <td className="px-4 py-3">
                  <form action="/api/admin/toggle-user-block" method="POST">
                    <input type="hidden" name="user_id" value={user.user_id} />
                    <button
                      type="submit"
                      className={`rounded-[var(--radius)] px-2.5 py-1 text-xs font-semibold transition ${
                        user.is_blocked
                          ? 'bg-[var(--success)]/10 text-[var(--success)] hover:bg-[var(--success)]/20'
                          : 'bg-[var(--danger)]/10 text-[var(--danger)] hover:bg-[var(--danger)]/20'
                      }`}
                    >
                      {user.is_blocked ? 'رفع مسدودیت' : 'مسدود'}
                    </button>
                  </form>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
