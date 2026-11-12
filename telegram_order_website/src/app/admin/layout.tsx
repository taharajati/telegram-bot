import { PanelShell } from '@/components/panel/panel-shell';
import { getAdminContext } from '@/lib/panel';

export default async function AdminRootLayout({ children }: { children: React.ReactNode }) {
  await getAdminContext();
  return (
    <PanelShell variant="admin" title="مدیریت فروشگرام" subtitle="پنل ادمین">
      {children}
    </PanelShell>
  );
}
