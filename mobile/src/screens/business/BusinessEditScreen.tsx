import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api, ApiError, imageUrl } from '../../api/client';
import { useAuth } from '../../auth';
import { ImageUploadButton } from '../../components';
import { confirm, useToast } from '../../feedback';
import { useRefData } from '../../refdata';
import { colors, space } from '../../theme';
import { Badge, Button, Card, ErrorView, Field, Loading, Notice, Row, Screen, SectionTitle, Select, T, Thumb, Toggle } from '../../ui';

const EMPTY = {
  name: '', description: '', category: null as number | null, city: null as number | null, area: null as number | null,
  public_phone: '', public_whatsapp: '', contact_consent: false, working_hours: '', pickup_available: true, delivery_available: false,
};

export default function BusinessEditScreen({ navigation }: any) {
  const { me, refreshMe } = useAuth();
  const { offerCategories, cities } = useRefData();
  const toast = useToast();
  const exists = !!me?.business_profile_id;
  const [form, setForm] = useState({ ...EMPTY });
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(exists);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const p = await api('/my/business/');
      setProfile(p);
      setForm({
        name: p.name, description: p.description, category: p.category, city: p.city, area: p.area, public_phone: p.public_phone,
        public_whatsapp: p.public_whatsapp, contact_consent: p.contact_consent, working_hours: p.working_hours,
        pickup_available: p.pickup_available, delivery_available: p.delivery_available,
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر التحميل');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    if (exists) load();
  }, [exists]);

  const set = (k: string) => (v: any) => setForm((f) => ({ ...f, [k]: v, ...(k === 'city' ? { area: null } : {}) }));
  const save = async () => {
    setError(null);
    try {
      const p = await api('/my/business/', { method: exists ? 'PATCH' : 'POST', body: form });
      setProfile(p);
      await refreshMe();
      toast(exists ? 'تم حفظ ملف المشروع.' : 'تم إنشاء مشروعك! أضف الآن منتجاتك وخدماتك.');
      if (!exists) navigation.replace('MyOffers');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر الحفظ');
    }
  };
  const removeImage = async (id: number) => {
    if (!(await confirm('حذف الصورة؟'))) return;
    await api(`/my/business/images/${id}/`, { method: 'DELETE' });
    load();
  };

  if (loading) return <Screen><Loading /></Screen>;
  const city = cities.find((c) => c.id === form.city);

  return (
    <Screen style={{ maxWidth: 680 }}>
      {profile?.status === 'suspended' ? <Notice tone="danger" text="مشروعك موقوف من إدارة المنصة ولا يظهر للعملاء حاليًا." /> : null}
      {!exists ? <Notice text="أنشئ ملف مشروعك المنزلي ليظهر للعملاء. يظهر للعامة المدينة والمنطقة فقط، لا عنوانك الدقيق." /> : null}
      <Card>
        <Field label="اسم المشروع *" value={form.name} onChangeText={set('name')} />
        <Field label="وصف مختصر" value={form.description} onChangeText={set('description')} multiline />
        <Select label="تصنيف النشاط *" options={offerCategories.map((c) => ({ value: c.id, label: c.name }))} value={form.category} onChange={set('category')} />
        <Select label="المدينة *" options={cities.map((c) => ({ value: c.id, label: c.name }))} value={form.city} onChange={set('city')} />
        {city?.areas.length ? <Select label="المنطقة" allowNone options={city.areas.map((a) => ({ value: a.id, label: a.name }))} value={form.area} onChange={set('area')} /> : null}
        <Field label="ساعات العمل" value={form.working_hours} onChangeText={set('working_hours')} placeholder="مثال: السبت - الخميس 9 - 6" />
        <Toggle label="استلام من المكان" value={form.pickup_available} onChange={set('pickup_available')} />
        <Toggle label="أوفر التوصيل" value={form.delivery_available} onChange={set('delivery_available')} />
      </Card>
      <Card>
        <T weight="bold">وسائل التواصل العامة</T>
        <Field label="هاتف للنشر" value={form.public_phone} onChangeText={set('public_phone')} keyboardType="phone-pad" />
        <Field label="واتساب للنشر" value={form.public_whatsapp} onChangeText={set('public_whatsapp')} keyboardType="phone-pad" />
        <Toggle label="أوافق على نشر وسائل التواصل أعلاه للعامة" value={form.contact_consent} onChange={set('contact_consent')} />
        <T size={12} color={colors.muted}>بدون الموافقة لن تظهر الأرقام، ويطلب العملاء عبر التطبيق.</T>
      </Card>
      {error ? <ErrorView message={error} /> : null}
      <Button title={exists ? 'حفظ التغييرات' : 'إنشاء المشروع'} onPress={save} disabled={!form.name || !form.category || !form.city} disabledReason="أكمل الحقول المطلوبة (*)" />

      {exists && profile ? (
        <>
          <SectionTitle title="الشعار" />
          <Card>
            <Row>
              <Thumb uri={imageUrl(profile.logo)} size={72} />
              <ImageUploadButton path="/my/business/logo/" onDone={load} title="تغيير الشعار" />
            </Row>
          </Card>
          <SectionTitle title="صور الأعمال" />
          <Card>
            <ScrollView horizontal contentContainerStyle={{ gap: space.sm }}>
              {profile.work_images.map((img: any) => (
                <View key={img.id}>
                  <Thumb uri={imageUrl(img.image)} size={100} />
                  <Pressable onPress={() => removeImage(img.id)} style={{ position: 'absolute', top: 4, left: 4, backgroundColor: '#fff', borderRadius: 12 }}>
                    <Ionicons name="close-circle" size={24} color={colors.danger} />
                  </Pressable>
                </View>
              ))}
            </ScrollView>
            <ImageUploadButton path="/my/business/images/" onDone={load} />
            <T size={12} color={colors.muted}>JPG أو PNG أو WEBP، حتى 5 ميغابايت.</T>
          </Card>
          <Row><Badge text={`التقييم: ${profile.rating_avg} (${profile.rating_count})`} tone="gold" /></Row>
        </>
      ) : null}
    </Screen>
  );
}
