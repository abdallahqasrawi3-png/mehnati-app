import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api, ApiError } from '../../api/client';
import { Material, Paged, SupplierCard } from '../../api/types';
import { MaterialCard } from '../../components';
import { useApi } from '../../hooks';
import { UNITS, useRefData } from '../../refdata';
import { colors, radius, space } from '../../theme';
import { Button, Card, Chips, Empty, ErrorView, Field, Loading, Row, Screen, SectionTitle, Select, T, Toggle } from '../../ui';

const ORDERING = [
  { value: 'newest', label: 'الأحدث' },
  { value: 'price', label: 'الأقل سعرًا' },
  { value: 'delivery', label: 'الأسرع توصيلًا' },
];

export default function MaterialsScreen({ navigation, route }: any) {
  const { materialCategories, cities } = useRefData();
  const [f, setF] = useState<any>({ q: '', category: route.params?.category ?? null, city: null, unit: null, max_price: '', max_delivery_days: '', min_available: '', delivery: false, ordering: 'newest' });
  const [show, setShow] = useState(false);
  const [items, setItems] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [compare, setCompare] = useState<number[]>([]);
  const suppliers = useApi<Paged<SupplierCard>>('/suppliers/');

  useEffect(() => {
    if (route.params?.category) setF((c: any) => ({ ...c, category: route.params.category }));
  }, [route.params]);

  useEffect(() => {
    const t = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const d = await api<Paged<Material>>('/materials/', { params: { ...f, delivery: f.delivery ? 1 : '' } });
        setItems(d.results);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : 'تعذر البحث');
      } finally {
        setLoading(false);
      }
    }, 350);
    return () => clearTimeout(t);
  }, [JSON.stringify(f)]);

  const set = (k: string) => (v: any) => setF((c: any) => ({ ...c, [k]: v }));
  const toggle = (id: number) => setCompare((c) => (c.includes(id) ? c.filter((x) => x !== id) : c.length >= 4 ? c : [...c, id]));

  return (
    <View style={{ flex: 1 }}>
      <Screen>
        <Field value={f.q} onChangeText={set('q')} placeholder="ابحث عن قماش، خيوط، أدوات…" />
        <Row style={{ justifyContent: 'space-between' }}>
          <Pressable onPress={() => setShow(!show)}>
            <Row gap={4}><Ionicons name="options-outline" size={20} color={colors.primary} /><T weight="semibold" color={colors.primary}>الفلاتر</T></Row>
          </Pressable>
          <Pressable onPress={() => navigation.navigate('SmartSearch', { target: 'materials', text: f.q })}>
            <Row gap={4}><Ionicons name="sparkles-outline" size={18} color={colors.gold} /><T weight="semibold" color={colors.gold}>المساعد الذكي</T></Row>
          </Pressable>
        </Row>
        {show ? (
          <Card>
            <Select label="التصنيف" allowNone options={materialCategories.map((c) => ({ value: c.id, label: c.name }))} value={f.category} onChange={set('category')} placeholder="الكل" />
            <Select label="موقع المورد" allowNone options={cities.map((c) => ({ value: c.id, label: c.name }))} value={f.city} onChange={set('city')} placeholder="كل المدن" />
            <T weight="semibold" size={14}>وحدة القياس</T>
            <Chips allowNone options={UNITS} value={f.unit} onChange={set('unit')} />
            <Row>
              <View style={{ flex: 1 }}><Field label="أعلى سعر للوحدة ₪" value={f.max_price} onChangeText={set('max_price')} keyboardType="numeric" /></View>
              <View style={{ flex: 1 }}><Field label="الوصول خلال (أيام)" value={f.max_delivery_days} onChangeText={set('max_delivery_days')} keyboardType="numeric" /></View>
            </Row>
            <Field label="الكمية التي أحتاجها (على الأقل متوفرة)" value={f.min_available} onChangeText={set('min_available')} keyboardType="numeric" />
            <Toggle label="يوفر التوصيل" value={f.delivery} onChange={set('delivery')} />
          </Card>
        ) : null}
        <Chips options={ORDERING} value={f.ordering} onChange={(v) => set('ordering')(v ?? 'newest')} />
        {suppliers.data?.results.length ? (
          <>
            <SectionTitle title="الموردون" />
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.sm }}>
              {suppliers.data.results.map((s) => (
                <Card key={s.id} onPress={() => navigation.navigate('Supplier', { id: s.id })} style={{ width: 180, padding: space.md }}>
                  <T weight="bold" numberOfLines={1}>{s.name}</T>
                  <T size={12} color={colors.muted}>{s.city_name} · {s.delivery_available ? 'توصيل' : 'استلام'}</T>
                </Card>
              ))}
            </ScrollView>
          </>
        ) : null}
        <SectionTitle title="المواد الخام" />
        {error ? <ErrorView message={error} /> : loading ? <Loading /> : !items.length ? (
          <Empty icon="layers-outline" title="لا توجد مواد مطابقة" subtitle="غيّر كلمات البحث أو الفلاتر." />
        ) : items.map((m) => <MaterialCard key={m.id} m={m} onToggleCompare={() => toggle(m.id)} inCompare={compare.includes(m.id)} />)}
      </Screen>
      {compare.length ? (
        <View style={{ position: 'absolute', bottom: 12, left: 12, right: 12, alignItems: 'center' }}>
          <View style={{ backgroundColor: colors.primaryDark, borderRadius: radius.lg, padding: space.sm, flexDirection: 'row', gap: space.sm, alignItems: 'center', maxWidth: 560, width: '100%' }}>
            <T color="#fff" style={{ flex: 1 }} size={13}>اخترت {compare.length} للمقارنة</T>
            <Button small variant="gold" title="قارن" disabled={compare.length < 2} onPress={() => navigation.navigate('Compare', { kind: 'materials', ids: compare })} />
            <Button small variant="secondary" title="مسح" onPress={() => setCompare([])} />
          </View>
        </View>
      ) : null}
    </View>
  );
}
