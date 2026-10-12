import React, { useState } from 'react';
import { Linking, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api, ApiError } from '../../api/client';
import { Address } from '../../api/types';
import { useAuth } from '../../auth';
import { confirm, useToast } from '../../feedback';
import { currentPosition, mapLink, parseCoordinates, Pin } from '../../geo';
import { useApi } from '../../hooks';
import { useRefData } from '../../refdata';
import { colors, radius, space } from '../../theme';
import { Badge, Button, Card, Chips, Empty, ErrorView, Field, Loading, Notice, Row, Screen, SectionTitle, Select, T } from '../../ui';

const LABELS = ['المنزل', 'المشغل', 'المستودع', 'العمل'];

type Form = {
  label: string; recipient_name: string; phone: string; city: number | null; area: number | null;
  street: string; building: string; floor: string; apartment: string; landmark: string; details: string;
  pin: Pin | null;
};

const EMPTY: Form = {
  label: 'المنزل', recipient_name: '', phone: '', city: null, area: null,
  street: '', building: '', floor: '', apartment: '', landmark: '', details: '', pin: null,
};

function fromAddress(a: Address): Form {
  return {
    label: a.label, recipient_name: a.recipient_name, phone: a.phone, city: a.city, area: a.area,
    street: a.street, building: a.building, floor: a.floor, apartment: a.apartment, landmark: a.landmark, details: a.details,
    pin: a.latitude !== null && a.longitude !== null ? { latitude: a.latitude, longitude: a.longitude } : null,
  };
}

function PinPicker({ pin, onChange }: { pin: Pin | null; onChange: (p: Pin | null) => void }) {
  const toast = useToast();
  const [paste, setPaste] = useState('');
  const [busy, setBusy] = useState(false);

  const useGps = async () => {
    setBusy(true);
    try {
      const p = await currentPosition();
      onChange(p);
      toast(p.accuracy ? `تم تحديد موقعك (بدقة تقارب ${Math.round(p.accuracy)} م).` : 'تم تحديد موقعك.');
    } catch (e: any) {
      toast(e?.message ?? 'تعذر تحديد الموقع', 'error');
    } finally {
      setBusy(false);
    }
  };
  const usePaste = () => {
    const p = parseCoordinates(paste);
    if (!p) {
      toast('لم أجد إحداثيات في النص. افتح الموقع في خرائط Google وانسخ الرابط الكامل أو الإحداثيات (مثل 32.2211, 35.2544).', 'error');
      return;
    }
    onChange(p);
    setPaste('');
    toast('تم حفظ الموقع من الرابط.');
  };

  return (
    <View style={{ gap: space.sm, padding: space.md, borderRadius: radius.md, backgroundColor: colors.primarySoft }}>
      <Row>
        <Ionicons name="location" size={18} color={colors.primary} />
        <T weight="bold">الموقع الدقيق على الخريطة (اختياري)</T>
      </Row>
      {pin ? (
        <>
          <Row wrap>
            <Badge text={`${pin.latitude.toFixed(6)}, ${pin.longitude.toFixed(6)}`} tone="primary" />
            {pin.accuracy ? <Badge text={`الدقة ≈ ${Math.round(pin.accuracy)} م`} tone={pin.accuracy > 100 ? 'warning' : 'success'} /> : null}
          </Row>
          {pin.accuracy && pin.accuracy > 100 ? <T size={12} color={colors.warning}>الدقة ضعيفة؛ جرّب في مكان مكشوف أو الصق الموقع من الخرائط.</T> : null}
          <Row wrap>
            <Button small variant="outline" icon="map-outline" title="عرض على الخريطة" onPress={() => Linking.openURL(mapLink(pin.latitude, pin.longitude))} />
            <Button small variant="ghost" icon="close-circle-outline" title="إزالة الموقع" onPress={() => onChange(null)} />
          </Row>
        </>
      ) : (
        <T size={12} color={colors.muted}>يساعد السائق أو المورد على الوصول مباشرة إلى الباب، خاصة في المناطق بلا أسماء شوارع واضحة.</T>
      )}
      <Button small icon="navigate-outline" title={pin ? 'تحديث إلى موقعي الحالي' : 'استخدم موقعي الحالي'} loading={busy} onPress={useGps} />
      <Field value={paste} onChangeText={setPaste} placeholder="أو الصق رابط خرائط Google أو الإحداثيات" autoCapitalize="none" />
      {paste.trim() ? <Button small variant="outline" title="استخدام هذا الموقع" onPress={usePaste} /> : null}
    </View>
  );
}

export default function AddressesScreen() {
  const list = useApi<Address[]>('/addresses/');
  const { cities } = useRefData();
  const { me } = useAuth();
  const toast = useToast();
  const [form, setForm] = useState<Form>({ ...EMPTY });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const city = cities.find((c) => c.id === form.city);
  const set = <K extends keyof Form>(k: K) => (v: Form[K]) => setForm((f) => ({ ...f, [k]: v }));

  const reset = () => {
    setForm({ ...EMPTY });
    setEditingId(null);
    setError(null);
  };

  const save = async () => {
    setError(null);
    const { pin, ...rest } = form;
    const body = { ...rest, latitude: pin?.latitude ?? null, longitude: pin?.longitude ?? null };
    try {
      await api(editingId ? `/addresses/${editingId}/` : '/addresses/', { method: editingId ? 'PATCH' : 'POST', body });
      toast(editingId ? 'تم تحديث العنوان.' : 'تمت إضافة العنوان.');
      reset();
      list.reload();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر الحفظ');
    }
  };
  const remove = async (id: number) => {
    if (!(await confirm('حذف العنوان؟', 'الطلبات السابقة تحتفظ بنسختها من العنوان.'))) return;
    try {
      await api(`/addresses/${id}/`, { method: 'DELETE' });
      if (editingId === id) reset();
      list.reload();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر الحذف', 'error');
    }
  };
  const edit = (a: Address) => {
    setForm(fromAddress(a));
    setEditingId(a.id);
    setError(null);
  };

  const canSave = !!form.city && !!form.recipient_name.trim() && !!form.phone.trim() && !!(form.street.trim() || form.landmark.trim() || form.details.trim());

  return (
    <Screen style={{ maxWidth: 680 }}>
      <Notice text="عناوينك خاصة. لا يراها إلا البائع أو المورد الذي تطلب منه التوصيل، وذلك لتنفيذ طلبك فقط." />
      {me?.business_profile_id ? (
        <Notice tone="success" text="لصاحب المشروع: أضف عنوان المشغل أو المستودع مع الطابق ومعلم قريب وموقع على الخريطة، ليصل الموردون مباشرة عند توصيل المواد الخام." />
      ) : null}

      {list.loading ? <Loading /> : list.error ? <ErrorView message={list.error} onRetry={list.reload} /> : !list.data?.length ? (
        <Empty icon="location-outline" title="لا توجد عناوين" subtitle="أضف عنوانًا لتتمكن من طلب التوصيل." />
      ) : list.data.map((a) => (
        <Card key={a.id} style={editingId === a.id ? { borderColor: colors.gold, borderWidth: 1.5 } : null}>
          <Row style={{ justifyContent: 'space-between' }}>
            <Row>
              <T weight="bold">{a.label}</T>
              {a.map_url ? <Badge text="موقع محدد" tone="success" /> : null}
            </Row>
            <Row gap={0}>
              <Button small variant="ghost" title="تعديل" icon="create-outline" onPress={() => edit(a)} />
              <Button small variant="ghost" title="حذف" icon="trash-outline" onPress={() => remove(a.id)} />
            </Row>
          </Row>
          <T>{a.recipient_name} · {a.phone}</T>
          <T color={colors.muted}>{a.city_name}{a.area_name ? ` - ${a.area_name}` : ''}</T>
          {a.full_text ? <T color={colors.muted}>{a.full_text}</T> : null}
          {a.map_url ? (
            <Button small variant="outline" icon="map-outline" title="فتح الموقع على الخريطة" onPress={() => Linking.openURL(a.map_url!)} />
          ) : null}
        </Card>
      ))}

      <SectionTitle title={editingId ? 'تعديل العنوان' : 'إضافة عنوان'} action={editingId ? <Button small variant="ghost" title="إلغاء التعديل" onPress={reset} /> : undefined} />
      <Card>
        <T weight="semibold" size={14}>اسم العنوان</T>
        <Chips options={LABELS.map((l) => ({ value: l, label: l }))} value={LABELS.includes(form.label) ? form.label : null} onChange={(v) => v && set('label')(v)} />
        <Field value={form.label} onChangeText={set('label')} placeholder="أو اكتب اسمًا آخر" />
        <Row>
          <View style={{ flex: 1 }}><Field label="اسم المستلم *" value={form.recipient_name} onChangeText={set('recipient_name')} /></View>
          <View style={{ flex: 1 }}><Field label="هاتف المستلم *" value={form.phone} onChangeText={set('phone')} keyboardType="phone-pad" /></View>
        </Row>
        <Select label="المدينة *" options={cities.map((c) => ({ value: c.id, label: c.name }))} value={form.city} onChange={(v) => setForm((f) => ({ ...f, city: v, area: null }))} />
        {city?.areas.length ? <Select label="المنطقة" allowNone options={city.areas.map((x) => ({ value: x.id, label: x.name }))} value={form.area} onChange={set('area')} /> : null}
        <Field label="الشارع" value={form.street} onChangeText={set('street')} placeholder="مثال: شارع رفيديا" />
        <Row>
          <View style={{ flex: 1 }}><Field label="البناية" value={form.building} onChangeText={set('building')} placeholder="رقم/اسم" /></View>
          <View style={{ flex: 1 }}><Field label="الطابق" value={form.floor} onChangeText={set('floor')} placeholder="مثال: 3" /></View>
          <View style={{ flex: 1 }}><Field label="الشقة/المحل" value={form.apartment} onChangeText={set('apartment')} /></View>
        </Row>
        <Field label="أقرب معلم" value={form.landmark} onChangeText={set('landmark')} placeholder="مثال: مقابل مدرسة البنات" />
        <Field label="تفاصيل إضافية" value={form.details} onChangeText={set('details')} multiline placeholder="لون الباب، المدخل الخلفي، أوقات الاستلام…" />
        <T size={12} color={colors.muted}>يجب ملء الشارع أو أقرب معلم أو التفاصيل على الأقل.</T>
        <PinPicker pin={form.pin} onChange={set('pin')} />
        {error ? <ErrorView message={error} /> : null}
        <Button title={editingId ? 'حفظ التعديلات' : 'حفظ العنوان'} icon="checkmark-circle-outline" onPress={save} disabled={!canSave} disabledReason="أكمل الحقول المطلوبة (*) واكتب الشارع أو معلمًا قريبًا" />
      </Card>
    </Screen>
  );
}
