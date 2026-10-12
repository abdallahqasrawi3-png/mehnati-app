import React, { useEffect, useState } from 'react';
import { View } from 'react-native';
import { api, ApiError } from '../../api/client';
import { useAuth } from '../../auth';
import { useToast } from '../../feedback';
import { useRefData } from '../../refdata';
import { colors } from '../../theme';
import { Button, Card, ErrorView, Field, Loading, Notice, Row, Screen, Select, T, Toggle } from '../../ui';

const EMPTY = {
  name: '', description: '', city: null as number | null, area: null as number | null, public_phone: '', contact_consent: false,
  pickup_available: true, delivery_available: false, delivery_cost: '', delivery_days: '',
};

export default function SupplierEditScreen({ navigation }: any) {
  const { me, refreshMe } = useAuth();
  const { cities } = useRefData();
  const toast = useToast();
  const exists = !!me?.supplier_profile_id;
  const [form, setForm] = useState({ ...EMPTY });
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(exists);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!exists) return;
    api('/my/supplier/')
      .then((p) => {
        setStatus(p.status);
        setForm({ ...p, delivery_cost: p.delivery_cost ?? '', delivery_days: p.delivery_days === null ? '' : String(p.delivery_days) });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [exists]);

  const set = (k: string) => (v: any) => setForm((f) => ({ ...f, [k]: v, ...(k === 'city' ? { area: null } : {}) }));
  const save = async () => {
    setError(null);
    const body = {
      name: form.name, description: form.description, city: form.city, area: form.area, public_phone: form.public_phone,
      contact_consent: form.contact_consent, pickup_available: form.pickup_available, delivery_available: form.delivery_available,
      delivery_cost: form.delivery_cost === '' ? null : form.delivery_cost, delivery_days: form.delivery_days === '' ? null : Number(form.delivery_days),
    };
    try {
      await api('/my/supplier/', { method: exists ? 'PATCH' : 'POST', body });
      await refreshMe();
      toast(exists ? 'تم الحفظ.' : 'تم إنشاء ملف المورد! أضف موادك الآن.');
      if (!exists) navigation.replace('MyMaterials');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر الحفظ');
    }
  };
  if (loading) return <Screen><Loading /></Screen>;
  const city = cities.find((c) => c.id === form.city);
  return (
    <Screen style={{ maxWidth: 640 }}>
      {status === 'suspended' ? <Notice tone="danger" text="ملف المورد موقوف من الإدارة." /> : null}
      <Card>
        <Field label="الاسم التجاري *" value={form.name} onChangeText={set('name')} />
        <Field label="الوصف" value={form.description} onChangeText={set('description')} multiline />
        <Select label="المدينة *" options={cities.map((c) => ({ value: c.id, label: c.name }))} value={form.city} onChange={set('city')} />
        {city?.areas.length ? <Select label="المنطقة" allowNone options={city.areas.map((a) => ({ value: a.id, label: a.name }))} value={form.area} onChange={set('area')} /> : null}
        <Field label="هاتف للنشر" value={form.public_phone} onChangeText={set('public_phone')} keyboardType="phone-pad" />
        <Toggle label="أوافق على نشر الهاتف" value={form.contact_consent} onChange={set('contact_consent')} />
        <Toggle label="الاستلام من عندي" value={form.pickup_available} onChange={set('pickup_available')} />
        <Toggle label="أوفر التوصيل" value={form.delivery_available} onChange={set('delivery_available')} />
        {form.delivery_available ? (
          <Row>
            <View style={{ flex: 1 }}><Field label="تكلفة التوصيل التقديرية ₪" value={String(form.delivery_cost)} onChangeText={set('delivery_cost')} keyboardType="decimal-pad" /></View>
            <View style={{ flex: 1 }}><Field label="مدة الوصول (أيام)" value={String(form.delivery_days)} onChangeText={set('delivery_days')} keyboardType="numeric" /></View>
          </Row>
        ) : null}
        <T size={12} color={colors.muted}>تكلفة التوصيل هنا تقديرية، ويمكنك تعديلها لكل طلب.</T>
        {error ? <ErrorView message={error} /> : null}
        <Button title={exists ? 'حفظ' : 'إنشاء ملف المورد'} onPress={save} disabled={!form.name || !form.city} disabledReason="أكمل الحقول المطلوبة" />
      </Card>
    </Screen>
  );
}
