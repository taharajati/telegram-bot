import type { Metadata } from 'next';
import { PageHeader } from '@/components/ui/states';
import { PasswordForm } from '@/components/panel/password-form';

export const metadata: Metadata = { title: 'تنظیمات' };

export default function AdminSettingsPage() {
  return (
    <div>
      <PageHeader title="تنظیمات" description="رمز ورود به پنل ادمین." />
      <div className="max-w-md"><PasswordForm /></div>
    </div>
  );
}
