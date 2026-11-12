import type { Metadata } from 'next';
import { LegalList, LegalPage, LegalSection } from '@/components/site/legal';

export const metadata: Metadata = {
  title: 'حریم خصوصی',
  description: 'سیاست حفظ حریم خصوصی کاربران فروشگرام',
};

export default function PrivacyPage() {
  return (
    <LegalPage title="حریم خصوصی" updated="تیر ۱۴۰۵">
      <LegalSection title="۱. اطلاعاتی که جمع‌آوری می‌کنیم">
        <p>برای ارائه‌ی خدمات، اطلاعات زیر را ذخیره می‌کنیم:</p>
        <LegalList
          items={[
            <><strong className="text-ink">شناسه تلگرام</strong> — برای احراز هویت و ارسال نوتیفیکیشن</>,
            <><strong className="text-ink">نام و نام خانوادگی</strong> — جهت درج در سفارش</>,
            <><strong className="text-ink">شماره تماس</strong> — برای هماهنگی ارسال</>,
            <><strong className="text-ink">آدرس</strong> — برای ارسال کالا</>,
            <><strong className="text-ink">اطلاعات پرداخت</strong> — شماره کارت فروشنده و رسیدهای واریز (به‌صورت رمزگذاری‌شده)</>,
          ]}
        />
      </LegalSection>
      <LegalSection title="۲. نحوه‌ی استفاده از اطلاعات">
        <p>
          اطلاعات شما صرفاً برای پردازش سفارش‌ها، ارسال نوتیفیکیشن و بهبود خدمات استفاده می‌شود. اطلاعات تماس شما
          در اختیار فروشنده‌ی مرتبط با سفارش قرار می‌گیرد — نه بیشتر.
        </p>
      </LegalSection>
      <LegalSection title="۳. اشتراک‌گذاری اطلاعات">
        <p>
          فروشگرام اطلاعات شما را به هیچ شخص ثالثی نمی‌فروشد. اطلاعات فقط در موارد قانونی (مثلاً حکم قضایی) یا
          برای پردازش سفارش (اشتراک با فروشنده‌ی مربوطه) منتشر می‌شود.
        </p>
      </LegalSection>
      <LegalSection title="۴. امنیت">
        <p>
          رمز عبور فروشندگان با الگوریتم bcrypt هش می‌شود. ارتباط با سرور از طریق HTTPS رمزگذاری شده است. با این
          حال، هیچ روش ذخیره‌سازی در اینترنت ۱۰۰٪ امن نیست و ما نمی‌توانیم امنیت مطلق را تضمین کنیم.
        </p>
      </LegalSection>
      <LegalSection title="۵. حقوق شما">
        <p>
          شما می‌توانید درخواست حذف حساب کاربری و اطلاعات خود را از طریق ربات تلگرام (دستور <bdi dir="ltr">/support</bdi>) ثبت کنید.
        </p>
      </LegalSection>
    </LegalPage>
  );
}
