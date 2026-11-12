import type { Metadata } from 'next';
import { LegalPage, LegalSection } from '@/components/site/legal';
import { botUrl, BOT_USERNAME } from '@/lib/utils';

export const metadata: Metadata = {
  title: 'درباره‌ی ما',
  description: 'درباره‌ی پلتفرم فروشگرام — فروشگاه تلگرامی با مدیریت خودکار سفارش',
};

export default function AboutPage() {
  return (
    <LegalPage title="درباره‌ی فروشگرام">
      <LegalSection title="فروشگرام چیست؟">
        <p>
          فروشگرام یک پلتفرم چندفروشگاهی است که به فروشنده‌ها اجازه می‌دهد فروشگاه خود را در تلگرام راه بیندازند.
          هر فروشنده فروشگاه جدا و اطلاعات جدا دارد؛ مشتری‌ها از طریق ربات سفارش می‌دهند و فروشنده‌ها سفارش‌ها را
          از ربات یا پنل سایت مدیریت می‌کنند.
        </p>
      </LegalSection>
      <LegalSection title="چطور کار می‌کند؟">
        <ol className="list-decimal space-y-3 ps-6">
          <li><strong className="text-ink">ثبت‌نام:</strong> فروشنده در ربات نام فروشگاه، شماره تماس، شماره کارت و نام صاحب کارت را وارد می‌کند.</li>
          <li><strong className="text-ink">مدیریت:</strong> محصول‌ها، دسته‌بندی‌ها و سفارش‌ها از ربات یا پنل سایت مدیریت می‌شود.</li>
          <li><strong className="text-ink">فروش:</strong> مشتری از لینک تلگرامی وارد می‌شود، سفارش می‌دهد و کارت‌به‌کارت پرداخت می‌کند.</li>
          <li><strong className="text-ink">تأیید:</strong> فروشنده رسید را بررسی و سفارش را تأیید یا رد می‌کند.</li>
        </ol>
      </LegalSection>
      <LegalSection title="ارتباط با ما">
        <p>
          ربات تلگرام:{' '}
          <a href={botUrl()} className="font-semibold text-brand underline-offset-4 hover:underline" dir="ltr">@{BOT_USERNAME}</a>
        </p>
        <p>پشتیبانی: از طریق ربات و دستور <bdi dir="ltr">/support</bdi></p>
      </LegalSection>
      <LegalSection title="اینماد">
        <p>فروشگرام در فرآیند اخذ نماد اعتماد الکترونیکی (اینماد) قرار دارد.</p>
      </LegalSection>
    </LegalPage>
  );
}
