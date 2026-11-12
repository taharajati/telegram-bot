import { PanelShell } from '@/components/panel/panel-shell';
import { getSellerContext } from '@/lib/panel';

export default async function SellerRootLayout({ children }: { children: React.ReactNode }) {
  const { shop } = await getSellerContext();
  return (
    <PanelShell variant="seller" title={shop.name} subtitle="پنل فروشنده" publicHref={`/shop/${shop.id}`}>
      {children}
    </PanelShell>
  );
}
