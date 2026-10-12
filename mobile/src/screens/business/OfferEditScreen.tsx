import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api, ApiError, imageUrl } from '../../api/client';
import { ImageUploadButton } from '../../components';
import { confirm, useToast } from '../../feedback';
import { OFFER_TYPES, useRefData } from '../../refdata';
import { colors, dateTimeText, space } from '../../theme';
import { Badge, Button, Card, Chips, ErrorView, Field, KV, Loading, Notice, Row, Screen, SectionTitle, Select, T, Thumb, Toggle } from '../../ui';

const EMPTY = {
  title: '', description: '', category: null as number | null, offer_type: 'ready', price: '', price_unit: 'للقطعة', unit_cost: '',
  preparation_days: '0', service_duration: '', is_available: true, low_stock_threshold: '0', initial_stock: '',
};

function StockPanel({ offer, onChange }: { offer: any; onChange: () => void }) {
  const toast = useToast();
  const [delta, setDelta] = useState('');
  const [note, setNote] = useState('');
  const [moves, setMoves] = useState<any[] | null>(null);
  const loadMoves = async () => setMoves(await api(`/my/offers/${offer.id}/movements/`));
  useEffect(() => { loadMoves().catch(() => {}); }, [offer.stock_quantity, offer.reserved_quantity]);
  const apply = async (sign: 1 | -1) => {
    const n = Number(delta);
    if (!Number.isInteger(n) || n <= 0) return toast('أدخل عددًا صحيحًا موجبًا.', 'error');
    try {
      await api(`/my/offers/${offer.id}/stock/`, { method: 'POST', body: { delta: sign * n, note } });
      setDelta('');
      setNote('');
      toast('تم تحديث المخزون.');
      onChange();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر التحديث', 'error');
    }
  };
  return (
    <Card>
      <T weight="bold">المخزون</T>
      <KV k="في المخزون" v={String(offer.stock_quantity)} />
      <KV k="محجوز لطلبات قائمة" v={String(offer.reserved_quantity)} />
      <KV k="متاح للبيع" v={String(offer.available_quantity)} />
      <Field label="الكمية" value={delta} onChangeText={setDelta} keyboardType="numeric" />
      <Field value={note} onChangeText={setNote} placeholder="السبب (إنتاج جديد، تالف…)" />
      <Row>
        <Button style={{ flex: 1 }} title="إضافة" icon="add" onPress={() => apply(1)} />
        <Button style={{ flex: 1 }} title="خصم" icon="remove" variant="outline" onPress={() => apply(-1)} />
      </Row>
      <T size={12} color={colors.muted}>لا يمكن أن يقل المخزون عن الكمية المحجوزة للطلبات.</T>
      <T weight="semibold" size={14}>سجل الحركات</T>
      {(moves ?? []).slice(0, 15).map((m) => (
        <Row key={m.id} style={{ justifyContent: 'space-between' }}>
          <T size={12}>{m.kind_display}{m.note ? ` · ${m.note}` : ''}{m.sales_order ? ` · طلب #${m.sales_order}` : ''}</T>
          <T size={12} color={colors.muted}>{Number(m.quantity)} · {dateTimeText(m.created_at)}</T>
        </Row>
      ))}
    </Card>
  );
}

function MarketingDraft({ offerId, onUse }: { offerId: number; onUse: (text: string) => void }) {
  const toast = useToast();
  const [extra, setExtra] = useState('');
  const [draft, setDraft] = useState<{ draft: string; source: string; note: string } | null>(null);
  const gen = async () => {
    try {
      setDraft(await api('/ai/marketing-draft/', { method: 'POST', body: { offer_id: offerId, extra_facts: extra } }));
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر إنشاء المسودة', 'error');
    }
  };
  return (
    <Card>
      <Row><Ionicons name="sparkles" size={18} color={colors.gold} /><T weight="bold">مسودة وصف تسويقي</T></Row>
      <Field value={extra} onChangeText={setExtra} placeholder="معلومات حقيقية إضافية (اختياري): نوع القماش، المقاسات…" />
      <Button title="اكتب لي مسودة" variant="gold" onPress={gen} />
      {draft ? (
        <>
          <Badge text={draft.source === 'ai' ? 'بالذكاء الاصطناعي' : 'قالب مدمج'} tone="gold" />
          <Field multiline value={draft.draft} onChangeText={(t) => setDraft({ ...draft, draft: t })} />
          <Notice tone="warning" text={draft.note} />
          <Button title="استخدمها في الوصف (ثم احفظ)" variant="outline" onPress={() => onUse(draft.draft)} />
        </>
      ) : null}
    </Card>
  );
}

export default function OfferEditScreen({ route, navigation }: any) {
  const id: number | undefined = route.params?.id;
  const { offerCategories } = useRefData();
  const toast = useToast();
  const [form, setForm] = useState({ ...EMPTY });
  const [offer, setOffer] = useState<any>(null);
  const [loading, setLoading] = useState(!!id);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!id) return;
    try {
      const o = await api(`/my/offers/${id}/`);
      setOffer(o);
      setForm({
        title: o.title, description: o.description, category: o.category, offer_type: o.offer_type, price: o.price, price_unit: o.price_unit,
        unit_cost: o.unit_cost ?? '', preparation_days: String(o.preparation_days), service_duration: o.service_duration,
        is_available: o.is_available, low_stock_threshold: String(o.low_stock_threshold), initial_stock: '',
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر التحميل');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [id]);
  React.useLayoutEffect(() => navigation.setOptions({ title: id ? 'تعديل العرض' : 'عرض جديد' }), [id]);

  const set = (k: string) => (v: any) => setForm((f) => ({ ...f, [k]: v }));
  const save = async () => {
    setError(null);
    const body: any = { ...form, unit_cost: form.unit_cost === '' ? null : form.unit_cost, preparation_days: Number(form.preparation_days) || 0, low_stock_threshold: Number(form.low_stock_threshold) || 0 };
    if (id || form.offer_type !== 'ready' || !form.initial_stock) delete body.initial_stock;
    else body.initial_stock = Number(form.initial_stock);
    try {
      const o = await api(id ? `/my/offers/${id}/` : '/my/offers/', { method: id ? 'PATCH' : 'POST', body });
      toast('تم الحفظ.');
      if (!id) navigation.replace('OfferEdit', { id: o.id });
      else { setOffer(o); }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر الحفظ');
    }
  };
  const remove = async () => {
    if (!(await confirm('حذف العرض؟', 'سيختفي من البحث. الطلبات السابقة تبقى محفوظة كما هي.'))) return;
    try {
      await api(`/my/offers/${id}/`, { method: 'DELETE' });
      toast('تم حذف العرض.');
      navigation.goBack();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر الحذف', 'error');
    }
  };
  const removeImage = async (imgId: number) => {
    if (!(await confirm('حذف الصورة؟'))) return;
    await api(`/my/offers/${id}/images/${imgId}/`, { method: 'DELETE' });
    load();
  };

  if (loading) return <Screen><Loading /></Screen>;
  return (
    <Screen style={{ maxWidth: 720 }}>
      <Card>
        <T weight="semibold" size={14}>نوع العرض</T>
        <Chips options={OFFER_TYPES} value={form.offer_type} onChange={(v) => v && set('offer_type')(v)} />
        <T size={12} color={colors.muted}>
          {form.offer_type === 'ready' ? 'منتج جاهز بكمية محددة: يُحجز من المخزون عند الطلب.' : form.offer_type === 'service' ? 'خدمة بموعد أو مدة تنفيذ، بدون مخزون.' : 'يُصنع بعد الطلب، بدون مخزون.'}
        </T>
        <Field label="العنوان *" value={form.title} onChangeText={set('title')} />
        <Select label="التصنيف *" options={offerCategories.map((c) => ({ value: c.id, label: c.name }))} value={form.category} onChange={set('category')} />
        <Field label="الوصف" value={form.description} onChangeText={set('description')} multiline />
        <Row>
          <View style={{ flex: 1 }}><Field label="السعر ₪ *" value={String(form.price)} onChangeText={set('price')} keyboardType="decimal-pad" /></View>
          <View style={{ flex: 1 }}><Field label="وحدة السعر" value={form.price_unit} onChangeText={set('price_unit')} placeholder="للقطعة، للكيلو، للجلسة" /></View>
        </Row>
        <Field label="تكلفة الوحدة عليك ₪ (خاصة، للتقارير فقط)" value={String(form.unit_cost)} onChangeText={set('unit_cost')} keyboardType="decimal-pad" hint="لا تظهر للعملاء. تساعد في حساب الربح التقديري." />
        <Field label="مدة التجهيز (أيام)" value={form.preparation_days} onChangeText={set('preparation_days')} keyboardType="numeric" />
        {form.offer_type === 'service' ? <Field label="مدة تنفيذ الخدمة" value={form.service_duration} onChangeText={set('service_duration')} placeholder="ساعتان" /> : null}
        {form.offer_type === 'ready' ? (
          <Row>
            {!id ? <View style={{ flex: 1 }}><Field label="الكمية الأولية" value={form.initial_stock} onChangeText={set('initial_stock')} keyboardType="numeric" /></View> : null}
            <View style={{ flex: 1 }}><Field label="تنبيه عند وصول المتاح إلى" value={form.low_stock_threshold} onChangeText={set('low_stock_threshold')} keyboardType="numeric" /></View>
          </Row>
        ) : null}
        <Toggle label="متاح للطلب" value={form.is_available} onChange={set('is_available')} />
        {error ? <ErrorView message={error} /> : null}
        <Button title="حفظ" onPress={save} disabled={!form.title || !form.category || form.price === ''} disabledReason="أكمل الحقول المطلوبة (*)" />
      </Card>

      {offer ? (
        <>
          <SectionTitle title="الصور" />
          <Card>
            <ScrollView horizontal contentContainerStyle={{ gap: space.sm }}>
              {offer.images.map((img: any) => (
                <View key={img.id}>
                  <Thumb uri={imageUrl(img.image)} size={100} />
                  <Pressable onPress={() => removeImage(img.id)} style={{ position: 'absolute', top: 4, left: 4, backgroundColor: '#fff', borderRadius: 12 }}>
                    <Ionicons name="close-circle" size={24} color={colors.danger} />
                  </Pressable>
                </View>
              ))}
            </ScrollView>
            <ImageUploadButton path={`/my/offers/${offer.id}/images/`} onDone={load} />
          </Card>
          {offer.offer_type === 'ready' ? <StockPanel offer={offer} onChange={load} /> : null}
          <MarketingDraft offerId={offer.id} onUse={(t) => { set('description')(t); toast('وُضعت المسودة في الوصف. راجعها ثم اضغط حفظ.', 'info'); }} />
          <Button title="عرض كما يراه العملاء" variant="outline" icon="eye-outline" onPress={() => navigation.navigate('Offer', { id: offer.id })} />
          <Button title="حذف العرض" variant="danger" icon="trash-outline" onPress={remove} />
        </>
      ) : null}
    </Screen>
  );
}
