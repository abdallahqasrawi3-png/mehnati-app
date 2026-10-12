import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api, ApiError, imageUrl } from '../../api/client';
import { ImageUploadButton } from '../../components';
import { confirm, useToast } from '../../feedback';
import { UNITS, useRefData } from '../../refdata';
import { colors, dateTimeText, qty, space } from '../../theme';
import { Button, Card, Chips, ErrorView, Field, KV, Loading, Row, Screen, SectionTitle, Select, T, Thumb, Toggle } from '../../ui';

const EMPTY = {
  title: '', description: '', specifications: '', category: null as number | null, unit: 'piece', price: '',
  min_order_quantity: '1', preparation_days: '0', low_stock_threshold: '0', is_available: true, initial_stock: '',
};

export default function MaterialEditScreen({ route, navigation }: any) {
  const id: number | undefined = route.params?.id;
  const { materialCategories } = useRefData();
  const toast = useToast();
  const [form, setForm] = useState({ ...EMPTY });
  const [m, setM] = useState<any>(null);
  const [moves, setMoves] = useState<any[]>([]);
  const [delta, setDelta] = useState('');
  const [loading, setLoading] = useState(!!id);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!id) return;
    try {
      const x = await api(`/my/materials/${id}/`);
      setM(x);
      setForm({
        title: x.title, description: x.description, specifications: x.specifications, category: x.category, unit: x.unit, price: x.price,
        min_order_quantity: x.min_order_quantity, preparation_days: String(x.preparation_days), low_stock_threshold: x.low_stock_threshold,
        is_available: x.is_available, initial_stock: '',
      });
      setMoves(await api(`/my/materials/${id}/movements/`));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر التحميل');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [id]);
  React.useLayoutEffect(() => navigation.setOptions({ title: id ? 'تعديل المادة' : 'مادة جديدة' }), [id]);

  const set = (k: string) => (v: any) => setForm((f) => ({ ...f, [k]: v }));
  const save = async () => {
    setError(null);
    const body: any = { ...form, preparation_days: Number(form.preparation_days) || 0 };
    if (id || !form.initial_stock) delete body.initial_stock;
    try {
      const x = await api(id ? `/my/materials/${id}/` : '/my/materials/', { method: id ? 'PATCH' : 'POST', body });
      toast('تم الحفظ.');
      if (!id) navigation.replace('MaterialEdit', { id: x.id });
      else load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر الحفظ');
    }
  };
  const adjust = async (sign: 1 | -1) => {
    const n = Number(delta);
    if (!(n > 0)) return toast('أدخل كمية موجبة.', 'error');
    try {
      await api(`/my/materials/${id}/stock/`, { method: 'POST', body: { delta: sign * n } });
      setDelta('');
      toast('تم تحديث المخزون.');
      load();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر التحديث', 'error');
    }
  };
  const remove = async () => {
    if (!(await confirm('حذف المادة؟', 'طلبات الشراء السابقة تبقى محفوظة.'))) return;
    await api(`/my/materials/${id}/`, { method: 'DELETE' });
    navigation.goBack();
  };

  if (loading) return <Screen><Loading /></Screen>;
  return (
    <Screen style={{ maxWidth: 720 }}>
      <Card>
        <Field label="الاسم *" value={form.title} onChangeText={set('title')} />
        <Select label="التصنيف *" options={materialCategories.map((c) => ({ value: c.id, label: c.name }))} value={form.category} onChange={set('category')} />
        <T weight="semibold" size={14}>وحدة القياس *</T>
        <Chips options={UNITS} value={form.unit} onChange={(v) => v && set('unit')(v)} />
        <Field label="المواصفات" value={form.specifications} onChangeText={set('specifications')} multiline placeholder="الخامة، العرض، اللون، الوزن…" />
        <Field label="الوصف" value={form.description} onChangeText={set('description')} multiline />
        <Row>
          <View style={{ flex: 1 }}><Field label="سعر الوحدة ₪ *" value={String(form.price)} onChangeText={set('price')} keyboardType="decimal-pad" /></View>
          <View style={{ flex: 1 }}><Field label="الحد الأدنى للشراء" value={String(form.min_order_quantity)} onChangeText={set('min_order_quantity')} keyboardType="decimal-pad" /></View>
        </Row>
        <Row>
          <View style={{ flex: 1 }}><Field label="مدة التجهيز (أيام)" value={form.preparation_days} onChangeText={set('preparation_days')} keyboardType="numeric" /></View>
          <View style={{ flex: 1 }}><Field label="حد تنبيه المخزون" value={String(form.low_stock_threshold)} onChangeText={set('low_stock_threshold')} keyboardType="decimal-pad" /></View>
        </Row>
        {!id ? <Field label="الكمية المتاحة الأولية" value={form.initial_stock} onChangeText={set('initial_stock')} keyboardType="decimal-pad" /> : null}
        <Toggle label="متاحة للطلب" value={form.is_available} onChange={set('is_available')} />
        {error ? <ErrorView message={error} /> : null}
        <Button title="حفظ" onPress={save} disabled={!form.title || !form.category || !form.price} disabledReason="أكمل الحقول المطلوبة" />
      </Card>
      {m ? (
        <>
          <SectionTitle title="الصور" />
          <Card>
            <ScrollView horizontal contentContainerStyle={{ gap: space.sm }}>
              {m.images.map((img: any) => (
                <View key={img.id}>
                  <Thumb uri={imageUrl(img.image)} size={100} />
                  <Pressable onPress={async () => { await api(`/my/materials/${m.id}/images/${img.id}/`, { method: 'DELETE' }); load(); }} style={{ position: 'absolute', top: 4, left: 4, backgroundColor: '#fff', borderRadius: 12 }}>
                    <Ionicons name="close-circle" size={24} color={colors.danger} />
                  </Pressable>
                </View>
              ))}
            </ScrollView>
            <ImageUploadButton path={`/my/materials/${m.id}/images/`} onDone={load} />
          </Card>
          <Card>
            <T weight="bold">المخزون ({m.unit_display})</T>
            <KV k="المخزون" v={qty(m.stock_quantity)} />
            <KV k="محجوز لطلبات" v={qty(m.reserved_quantity)} />
            <KV k="متاح" v={qty(m.available_quantity)} />
            <Field label="الكمية" value={delta} onChangeText={setDelta} keyboardType="decimal-pad" />
            <Row>
              <Button style={{ flex: 1 }} title="إضافة" icon="add" onPress={() => adjust(1)} />
              <Button style={{ flex: 1 }} title="خصم" icon="remove" variant="outline" onPress={() => adjust(-1)} />
            </Row>
            {moves.slice(0, 15).map((x) => (
              <Row key={x.id} style={{ justifyContent: 'space-between' }}>
                <T size={12}>{x.kind_display}{x.purchase_order ? ` · طلب #${x.purchase_order}` : ''}</T>
                <T size={12} color={colors.muted}>{qty(x.quantity)} · {dateTimeText(x.created_at)}</T>
              </Row>
            ))}
          </Card>
          <Button title="حذف المادة" variant="danger" icon="trash-outline" onPress={remove} />
        </>
      ) : null}
    </Screen>
  );
}
