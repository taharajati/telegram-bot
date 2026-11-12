import type { Metadata } from 'next';
import { getSellerContext } from '@/lib/panel';
import { Card, CardTitle, DetailRow } from '@/components/ui/card';
import { PageHeader } from '@/components/ui/states';
import { PasswordForm } from '@/components/panel/password-form';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = { title: 'تنظیمات' };

export default async function SellerSettingsPage() {
  const { shop, owner } = await getSellerContext();
  return (
    <div>
      <PageHeader title="تنظیمات" description="اطلاعات حساب و رمز ورود به پنل." />
      <div className="grid max-w-4xl gap-6 lg:grid-cols-2">
        <Card as="section">
          <CardTitle>حساب فروشگاه</CardTitle>
          <dl className="mt-2">
            <DetailRow label="نام فروشگاه">{shop.name}</DetailRow>
            <DetailRow label="نام کاربری"><bdi dir="ltr">{owner.username || '—'}</bdi></DetailRow>
          </dl>
          <p className="mt-3 text-xs text-ink-subtle">نام و توضیحات فروشگاه از ربات تلگرام ویرایش می‌شود.</p>
        </Card>
        <PasswordForm />
      </div>
    </div>
  );
}
