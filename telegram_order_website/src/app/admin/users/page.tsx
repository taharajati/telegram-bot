import type { Metadata } from 'next';
import { Users } from 'lucide-react';
import { getAllUsers } from '@/lib/db';
import { formatDate, formatNumber } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { EmptyState, PageHeader } from '@/components/ui/states';
import { Table, Td, Th, Truncate } from '@/components/ui/table';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'کاربران' };

export default async function AdminUsersPage() {
  const users = await getAllUsers();

  return (
    <div>
      <PageHeader title="کاربران" description={`${formatNumber(users.length)} کاربر در ربات`} />
      {users.length > 0 ? (
        <Table caption="کاربران ربات">
          <thead>
            <tr><Th>شناسه</Th><Th>نام</Th><Th>نام کاربری</Th><Th>تلفن</Th><Th>وضعیت</Th><Th>تاریخ ثبت‌نام</Th><Th><span className="sr-only">عملیات</span></Th></tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.user_id} className="hover:bg-canvas">
                <Td className="text-ink-subtle tabular-nums" dir="ltr"><bdi>{u.user_id}</bdi></Td>
                <Td className="font-semibold">{u.first_name ? <Truncate max="max-w-40">{u.first_name}</Truncate> : '—'}</Td>
                <Td className="text-ink-muted" dir="ltr">{u.username ? <bdi>@{u.username}</bdi> : '—'}</Td>
                <Td className="text-ink-muted" dir="ltr"><bdi>{u.phone || '—'}</bdi></Td>
                <Td><Badge tone={u.is_blocked ? 'danger' : 'success'}>{u.is_blocked ? 'مسدود' : 'فعال'}</Badge></Td>
                <Td className="whitespace-nowrap text-ink-muted tabular-nums">{formatDate(u.registered_at)}</Td>
                <Td>
                  <form action="/api/admin/toggle-user-block" method="POST">
                    <input type="hidden" name="user_id" value={u.user_id} />
                    <button type="submit" className="inline-flex min-h-9 items-center rounded-sm border border-line-strong px-3 text-xs font-semibold hover:bg-canvas">
                      {u.is_blocked ? 'رفع مسدودیت' : 'مسدود کردن'}
                      <span className="sr-only"> {u.first_name || u.user_id}</span>
                    </button>
                  </form>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      ) : (
        <EmptyState icon={Users} title="هنوز کاربری ثبت‌نام نکرده" description="کاربران با اولین ورود به ربات اینجا نمایش داده می‌شوند." />
      )}
    </div>
  );
}
