// صفحه‌ی اصلی — مخاطب: فروشنده‌ای که می‌خواهد فروشگاه تلگرامی راه بیندازد.
import Link from 'next/link';
import {
  ArrowLeft, BarChart3, Bell, Check, CreditCard, Link2, MessageCircle, Package, ShieldCheck, Store, Tag, Truck,
} from 'lucide-react';
import { getActivePlans, getPublicShops } from '@/lib/queries';
import { botUrl, formatNumber } from '@/lib/utils';
import { buttonStyles } from '@/components/ui/button';

export const dynamic = 'force-dynamic';

const FREE_MODE = process.env.FREE_MODE; // 'true' | 'false' | undefined — فقط برای متن بخش پلن‌ها

const STEPS = [
  { t: 'ربات را باز کن', d: 'روی دکمه‌ی «ساخت فروشگاه در تلگرام» بزن تا ربات فروشگرام باز شود.' },
  { t: 'اطلاعات پایه را بفرست', d: 'نام فروشگاه، شماره تماس، شماره کارت و نام صاحب کارت را وارد کن.' },
  { t: 'محصول اضافه کن و لینک بده', d: 'محصول‌ها را از ربات یا پنل سایت اضافه کن و لینک فروشگاه را در کانال یا بیو بگذار.' },
];

const FEATURES = [
  { icon: CreditCard, t: 'پرداخت کارت‌به‌کارت مستقیم', d: 'مشتری رسید را در ربات می‌فرستد، تو تأیید یا رد می‌کنی و پول مستقیم به کارت خودت می‌رود.' },
  { icon: Package, t: 'موجودی بدون فروش مازاد', d: 'موجودی هنگام ثبت سفارش رزرو می‌شود؛ دو مشتری نمی‌توانند آخرین عدد را با هم بخرند.' },
  { icon: Tag, t: 'کد تخفیف', d: 'کد درصدی یا مبلغی با حداقل سفارش و سقف تعداد استفاده بساز.' },
  { icon: Truck, t: 'پیگیری سفارش برای مشتری', d: 'مشتری وضعیت را از ثبت سفارش تا تحویل در ربات می‌بیند.' },
  { icon: Bell, t: 'اعلان موجود شدن و سبد رها‌شده', d: 'اگر محصول تمام شده باشد، مشتری با «خبرم کن» وقتی موجود شد پیام می‌گیرد.' },
  { icon: Link2, t: 'لینک مستقیم', d: 'برای فروشگاه، دسته‌بندی و هر محصول یک لینک تلگرامی جدا داری.' },
  { icon: MessageCircle, t: 'گفت‌وگوی مشتری و فروشنده', d: 'مشتری از جزئیات سفارش پیام می‌دهد و تو از صندوق پیام ربات پاسخ می‌دهی.' },
  { icon: BarChart3, t: 'داشبورد فروش', d: 'فروش امروز، هفته و ماه، پرفروش‌ترین محصول‌ها و سفارش‌های منتظر اقدام.' },
  { icon: ShieldCheck, t: 'اطلاعات کارت رمزنگاری‌شده', d: 'شماره کارت با AES-256-GCM ذخیره می‌شود و فقط در مرحله‌ی پرداخت نشان داده می‌شود.' },
];

const FAQ = [
  { q: 'مشتری‌ها چطور پرداخت می‌کنند؟', a: 'فقط کارت‌به‌کارت. مشتری عکس رسید یا شماره تراکنش را در ربات می‌فرستد و فروشنده آن را تأیید یا رد می‌کند.' },
  { q: 'پول به کجا می‌رود؟', a: 'مستقیم به کارت خودت. فروشگرام واسطه‌ی مالی نیست و پولی نزد ما نمی‌ماند.' },
  { q: 'رمز ورود به پنل سایت را از کجا بگیرم؟', a: 'در ربات از بخش «تنظیمات سایت». اگر رمز را فراموش کردی، دستور /reset_password یک رمز موقت می‌دهد.' },
  { q: 'اگر موجودی محصول تمام شود چه می‌شود؟', a: 'محصول ناموجود نمایش داده می‌شود و مشتری می‌تواند «خبرم کن» را بزند تا با موجود شدن پیام بگیرد.' },
  { q: 'برای ساخت فروشگاه چه چیزی لازم است؟', a: 'یک حساب تلگرام. نیازی به برنامه‌نویسی یا طراحی سایت نیست.' },
];

const FLOW = ['ثبت سفارش', 'پرداخت', 'آماده‌سازی', 'ارسال', 'تحویل'];

export default async function HomePage() {
  const [plans, shops] = await Promise.all([
    getActivePlans().catch(() => []),
    getPublicShops({ limit: 6 }).catch(() => []),
  ]);

  return (
    <>
      {/* ── Hero ── */}
      <section className="border-b border-line bg-surface">
        <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-12 md:py-20 lg:grid-cols-[1.2fr_1fr]">
          <div>
            <p className="mb-3 text-sm font-semibold text-brand">پلتفرم فروشگاه تلگرامی</p>
            <h1 className="max-w-2xl text-3xl font-extrabold leading-snug text-ink md:text-5xl md:leading-snug">
              فروشگاه تلگرامی‌ات را در چند دقیقه راه بینداز
            </h1>
            <p className="mt-4 max-w-xl text-base text-ink-muted md:text-lg">
              سفارش‌ها، رسیدهای کارت‌به‌کارت و پیگیری مشتری‌ها در یک ربات و یک پنل مدیریت می‌شود. بدون
              برنامه‌نویسی و بدون واسطه‌ی مالی.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <a href={botUrl('newshop')} target="_blank" rel="noopener noreferrer" className={buttonStyles({ size: 'lg' })}>
                ساخت فروشگاه در تلگرام
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              </a>
              <Link href="/login" className={buttonStyles({ size: 'lg', variant: 'secondary' })}>
                ورود به پنل فروشنده
              </Link>
            </div>
            <p className="mt-4 text-sm text-ink-subtle">پول مستقیم به کارت خودت می‌رود · مدیریت از ربات و سایت</p>
          </div>

          {/* نمونه‌ی پیگیری سفارش — عنصر غالب صفحه */}
          <div className="rounded-md border border-line bg-canvas p-5" aria-label="نمونه‌ی پیگیری سفارش در ربات">
            <div className="mb-4 flex items-center justify-between gap-3">
              <p className="text-sm font-bold">پیگیری سفارش در ربات</p>
              <span className="rounded-sm border border-line-strong px-2 py-0.5 text-xs text-ink-muted">نمونه</span>
            </div>
            <ol className="space-y-0">
              {FLOW.map((step, i) => {
                const done = i < 2;
                const current = i === 2;
                return (
                  <li key={step} className="relative flex items-center gap-3 pb-5 last:pb-0">
                    {i < FLOW.length - 1 && (
                      <span aria-hidden="true" className={`absolute start-3 top-7 h-[calc(100%-20px)] w-px ${done ? 'bg-brand' : 'bg-line-strong'}`} />
                    )}
                    <span
                      className={`relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold ${
                        done ? 'border-brand bg-brand text-white' : current ? 'border-brand bg-surface text-brand' : 'border-line-strong bg-surface text-ink-subtle'
                      }`}
                    >
                      {done ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : formatNumber(i + 1)}
                    </span>
                    <span className={`text-sm ${current ? 'font-bold text-ink' : done ? 'text-ink' : 'text-ink-subtle'}`}>
                      {step}
                      {current && <span className="ms-2 text-xs font-semibold text-brand">(مرحله‌ی فعلی)</span>}
                    </span>
                  </li>
                );
              })}
            </ol>
          </div>
        </div>
      </section>

      {/* ── How ── */}
      <section id="how" className="scroll-mt-16 px-4 py-16">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-2xl font-extrabold">از صفر تا اولین سفارش</h2>
          <p className="mt-1 text-sm text-ink-muted">سه قدم، همه داخل تلگرام.</p>
          <ol className="mt-8 grid gap-6 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <li key={s.t} className="rounded-md border border-line bg-surface p-5">
                <p className="text-sm font-bold text-brand">قدم {formatNumber(i + 1)}</p>
                <h3 className="mt-1 text-lg font-bold">{s.t}</h3>
                <p className="mt-2 text-sm text-ink-muted">{s.d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="scroll-mt-16 border-y border-line bg-surface px-4 py-16">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-2xl font-extrabold">هر چیزی که یک فروشگاه تلگرامی لازم دارد</h2>
          <ul className="mt-8 grid gap-x-10 gap-y-6 md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <li key={f.t} className="flex gap-3">
                <f.icon className="mt-1 h-5 w-5 shrink-0 text-brand" aria-hidden="true" />
                <div>
                  <h3 className="font-bold">{f.t}</h3>
                  <p className="mt-1 text-sm text-ink-muted">{f.d}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* ── Pricing ── */}
      {plans.length > 0 && (
        <section id="pricing" className="scroll-mt-16 px-4 py-16">
          <div className="mx-auto max-w-6xl">
            <h2 className="text-2xl font-extrabold">پلن‌های اشتراک</h2>
            <p className="mt-1 text-sm text-ink-muted">
              {FREE_MODE === 'true'
                ? 'در حال حاضر استفاده از پلتفرم رایگان است؛ پلن‌ها برای زمان فعال شدن اشتراک است.'
                : FREE_MODE === 'false'
                  ? 'هر فروشگاه جدید ۱۳ روز دوره‌ی آزمایشی دارد؛ بعد از آن یکی از پلن‌ها را انتخاب کن.'
                  : 'پرداخت اشتراک هم کارت‌به‌کارت و از داخل ربات انجام می‌شود.'}
            </p>
            <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {plans.map((p) => (
                <li key={p.id} className="rounded-md border border-line bg-surface p-5">
                  <h3 className="font-bold">{p.name}</h3>
                  <p className="mt-1 text-sm text-ink-muted">اعتبار {formatNumber(p.duration_days)} روز</p>
                  <p className="mt-4 text-2xl font-extrabold tabular-nums">{formatNumber(p.price)}</p>
                  <p className="text-xs text-ink-subtle">تومان</p>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {/* ── Shops ── */}
      {shops.length > 0 && (
        <section className="border-y border-line bg-surface px-4 py-16">
          <div className="mx-auto max-w-6xl">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <h2 className="text-2xl font-extrabold">فروشگاه‌های فعال</h2>
              <Link href="/shops" className="text-sm font-semibold text-brand underline-offset-4 hover:underline">
                همه‌ی فروشگاه‌ها
              </Link>
            </div>
            <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {shops.map((s) => (
                <li key={s.id}>
                  <Link href={`/shop/${s.id}`} className="block rounded-md border border-line bg-surface p-4 transition-colors hover:border-brand">
                    <div className="flex items-center gap-3">
                      <Store className="h-5 w-5 shrink-0 text-brand" aria-hidden="true" />
                      <div className="min-w-0">
                        <h3 className="truncate font-bold" title={s.name}>{s.name}</h3>
                        <p className="truncate text-xs text-ink-subtle">
                          {s.product_count > 0 ? `${formatNumber(s.product_count)} محصول فعال` : 'هنوز محصولی اضافه نشده'}
                        </p>
                      </div>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {/* ── FAQ ── */}
      <section id="faq" className="scroll-mt-16 px-4 py-16">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-2xl font-extrabold">سؤال‌های پرتکرار</h2>
          <div className="mt-6 divide-y divide-line rounded-md border border-line bg-surface">
            {FAQ.map((f) => (
              <details key={f.q} className="group p-4">
                <summary className="flex min-h-8 items-center justify-between gap-4 font-semibold">
                  {f.q}
                  <span aria-hidden="true" className="text-brand transition-transform group-open:rotate-45">+</span>
                </summary>
                <p className="mt-2 text-sm text-ink-muted">{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="border-t border-line bg-surface px-4 py-14">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-extrabold">آماده‌ای اولین سفارش را بگیری؟</h2>
            <p className="mt-1 text-sm text-ink-muted">ساخت فروشگاه چند دقیقه بیشتر طول نمی‌کشد.</p>
          </div>
          <a href={botUrl('newshop')} target="_blank" rel="noopener noreferrer" className={buttonStyles({ variant: 'secondary', size: 'lg' })}>
            ساخت فروشگاه در تلگرام
          </a>
        </div>
      </section>
    </>
  );
}
