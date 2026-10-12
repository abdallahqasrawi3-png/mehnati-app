import React, { useState } from 'react';
import { ApiError } from '../../api/client';
import { useAuth } from '../../auth';
import { useToast } from '../../feedback';
import { useRefData } from '../../refdata';
import { colors } from '../../theme';
import { Button, Card, ErrorView, Field, Notice, Screen, Select, T } from '../../ui';

export default function RegisterScreen({ navigation }: any) {
  const { register } = useAuth();
  const toast = useToast();
  const { cities } = useRefData();
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', password: '', password2: '', city: null as number | null });
  const [error, setError] = useState<string | null>(null);
  const set = (k: string) => (v: any) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    setError(null);
    if (form.full_name.trim().length < 2) return setError('أدخل الاسم الكامل.');
    if (!form.email.includes('@')) return setError('أدخل بريدًا إلكترونيًا صحيحًا.');
    if (form.password.length < 8) return setError('كلمة المرور 8 أحرف على الأقل.');
    if (form.password !== form.password2) return setError('كلمتا المرور غير متطابقتين.');
    try {
      const { password2, ...body } = form;
      await register(body);
      toast('تم إنشاء حسابك. أهلًا بك في مهنتي!');
      navigation.goBack();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر إنشاء الحساب');
    }
  };

  return (
    <Screen style={{ maxWidth: 520 }}>
      <Notice text="كل حساب يمكنه الشراء كعميل. بعد التسجيل يمكنك أيضًا إنشاء ملف مشروع منزلي أو ملف مورد من صفحة «حسابي»." />
      <Card>
        <Field label="الاسم الكامل" value={form.full_name} onChangeText={set('full_name')} autoComplete="name" />
        <Field label="البريد الإلكتروني" value={form.email} onChangeText={set('email')} autoCapitalize="none" keyboardType="email-address" autoComplete="email" />
        <Field label="رقم الهاتف (خاص، لا يُنشر)" value={form.phone} onChangeText={set('phone')} keyboardType="phone-pad" />
        <Select label="المدينة" options={cities.map((c) => ({ value: c.id, label: c.name }))} value={form.city} onChange={set('city')} />
        <Field label="كلمة المرور" value={form.password} onChangeText={set('password')} secureTextEntry autoComplete="new-password" hint="8 أحرف على الأقل، ولا تكون أرقامًا فقط أو شائعة." />
        <Field label="تأكيد كلمة المرور" value={form.password2} onChangeText={set('password2')} secureTextEntry />
        {error ? <ErrorView message={error} /> : null}
        <Button title="إنشاء الحساب" onPress={submit} />
      </Card>
      <T center color={colors.muted}>لديك حساب؟</T>
      <Button title="تسجيل الدخول" variant="outline" onPress={() => navigation.replace('Login')} />
    </Screen>
  );
}
