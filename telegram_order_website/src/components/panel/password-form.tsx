'use client';

import { useState } from 'react';
import toast from 'react-hot-toast';
import { Loader2 } from 'lucide-react';
import { Card, CardTitle } from '@/components/ui/card';
import { Field, Input } from '@/components/ui/field';
import { buttonStyles } from '@/components/ui/button';

type Errors = { current?: string; next?: string; confirm?: string };

export function PasswordForm() {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [saving, setSaving] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const err: Errors = {};
    if (!current) err.current = 'رمز فعلی را وارد کن.';
    if (next.length < 6) err.next = 'رمز جدید باید دست‌کم ۶ نویسه باشد.';
    if (confirm !== next) err.confirm = 'تکرار رمز با رمز جدید یکسان نیست.';
    setErrors(err);
    if (Object.keys(err).length) return;

    setSaving(true);
    try {
      const res = await fetch('/api/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ currentPassword: current, newPassword: next }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.success) {
        toast.success('رمز عبور تغییر کرد.');
        setCurrent(''); setNext(''); setConfirm('');
      } else if (res.status === 401) {
        setErrors({ current: 'رمز فعلی اشتباه است.' });
      } else {
        toast.error(data.error || 'رمز تغییر نکرد. دوباره تلاش کن.');
      }
    } catch {
      toast.error('ارتباط با سرور برقرار نشد. اتصال را بررسی کن و دوباره تلاش کن.');
    } finally {
      setSaving(false);
    }
  }

  const inv = (m?: string) => (m ? true : undefined);

  return (
    <Card as="section">
      <CardTitle>تغییر رمز عبور</CardTitle>
      <form onSubmit={onSubmit} noValidate className="mt-4 space-y-4">
        <Field id="current" label="رمز فعلی" error={errors.current}>
          <Input id="current" type="password" dir="ltr" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} aria-invalid={inv(errors.current)} aria-describedby={errors.current ? 'current-error' : undefined} />
        </Field>
        <Field id="next" label="رمز جدید" hint="دست‌کم ۶ نویسه" error={errors.next}>
          <Input id="next" type="password" dir="ltr" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} aria-invalid={inv(errors.next)} aria-describedby={errors.next ? 'next-error' : 'next-hint'} />
        </Field>
        <Field id="confirm" label="تکرار رمز جدید" error={errors.confirm}>
          <Input id="confirm" type="password" dir="ltr" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} aria-invalid={inv(errors.confirm)} aria-describedby={errors.confirm ? 'confirm-error' : undefined} />
        </Field>
        <button type="submit" disabled={saving} className={buttonStyles()}>
          {saving && <Loader2 className="h-4 w-4 motion-safe:animate-spin" aria-hidden="true" />}
          ذخیره‌ی رمز جدید
        </button>
      </form>
    </Card>
  );
}
