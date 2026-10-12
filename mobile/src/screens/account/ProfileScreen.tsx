import React, { useState } from 'react';
import { api, ApiError } from '../../api/client';
import { useAuth } from '../../auth';
import { useToast } from '../../feedback';
import { useRefData } from '../../refdata';
import { Button, Card, ErrorView, Field, Screen, Select, T } from '../../ui';

export default function ProfileScreen() {
  const { me, refreshMe } = useAuth();
  const { cities } = useRefData();
  const toast = useToast();
  const [form, setForm] = useState({ full_name: me?.full_name ?? '', phone: me?.phone ?? '', city: me?.city ?? null });
  const [pw, setPw] = useState({ old_password: '', new_password: '' });
  const [error, setError] = useState<string | null>(null);
  const [pwError, setPwError] = useState<string | null>(null);

  const save = async () => {
    setError(null);
    try {
      await api('/auth/me/', { method: 'PATCH', body: form });
      await refreshMe();
      toast('تم حفظ بياناتك.');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر الحفظ');
    }
  };
  const changePw = async () => {
    setPwError(null);
    try {
      await api('/auth/change-password/', { method: 'POST', body: pw });
      setPw({ old_password: '', new_password: '' });
      toast('تم تغيير كلمة المرور.');
    } catch (e) {
      setPwError(e instanceof ApiError ? e.message : 'تعذر التغيير');
    }
  };

  return (
    <Screen style={{ maxWidth: 560 }}>
      <Card>
        <T weight="bold">البيانات الشخصية</T>
        <Field label="الاسم الكامل" value={form.full_name} onChangeText={(v) => setForm({ ...form, full_name: v })} />
        <Field label="الهاتف (خاص)" value={form.phone} onChangeText={(v) => setForm({ ...form, phone: v })} keyboardType="phone-pad" />
        <Select label="المدينة" options={cities.map((c) => ({ value: c.id, label: c.name }))} value={form.city} onChange={(v) => setForm({ ...form, city: v })} />
        {error ? <ErrorView message={error} /> : null}
        <Button title="حفظ" onPress={save} />
      </Card>
      <Card>
        <T weight="bold">تغيير كلمة المرور</T>
        <Field label="كلمة المرور الحالية" value={pw.old_password} onChangeText={(v) => setPw({ ...pw, old_password: v })} secureTextEntry />
        <Field label="كلمة المرور الجديدة" value={pw.new_password} onChangeText={(v) => setPw({ ...pw, new_password: v })} secureTextEntry />
        {pwError ? <ErrorView message={pwError} /> : null}
        <Button title="تغيير" variant="outline" onPress={changePw} disabled={!pw.old_password || pw.new_password.length < 8} />
      </Card>
    </Screen>
  );
}
