import React, { useEffect, useState } from 'react';
import { Pressable, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api, ApiError } from '../../api/client';
import { Offer, Paged } from '../../api/types';
import { OfferCard } from '../../components';
import { OFFER_TYPES, useRefData } from '../../refdata';
import { colors, radius, space } from '../../theme';
import { Button, Card, Chips, Empty, ErrorView, Field, Loading, Row, Screen, Select, T, Toggle } from '../../ui';

const ORDERING = [
  { value: 'newest', label: 'الأحدث' },
  { value: 'price', label: 'الأقل سعرًا' },
  { value: '-price', label: 'الأعلى سعرًا' },
  { value: 'rating', label: 'الأعلى تقييمًا' },
  { value: 'prep', label: 'الأسرع تجهيزًا' },
];

type Filters = {
  q: string; category: number | null; city: number | null; area: number | null; min_price: string; max_price: string;
  min_rating: number | null; max_prep_days: string; offer_type: string | null; available: boolean; delivery: boolean; ordering: string;
};

const EMPTY: Filters = { q: '', category: null, city: null, area: null, min_price: '', max_price: '', min_rating: null, max_prep_days: '', offer_type: null, available: false, delivery: false, ordering: 'newest' };

export default function SearchScreen({ navigation, route }: any) {
  const { offerCategories, cities } = useRefData();
  const [f, setF] = useState<Filters>({ ...EMPTY, q: route.params?.q ?? '', category: route.params?.category ?? null });
  const [showFilters, setShowFilters] = useState(false);
  const [items, setItems] = useState<Offer[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [compare, setCompare] = useState<number[]>([]);

  // Apply params when navigated to from Home/categories
  useEffect(() => {
    if (route.params) {
      setF((cur) => ({ ...cur, q: route.params.q ?? cur.q, category: route.params.category ?? (route.params.q !== undefined ? null : cur.category) }));
    }
  }, [route.params]);

  const run = async (p = 1, filters = f) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api<Paged<Offer>>('/offers/', {
        params: { ...filters, available: filters.available ? 1 : '', delivery: filters.delivery ? 1 : '', page: p },
      });
      setItems(p === 1 ? data.results : [...items, ...data.results]);
      setCount(data.count);
      setHasNext(!!data.next);
      setPage(p);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر البحث');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const t = setTimeout(() => run(1, f), 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(f)]);

  const set = (k: keyof Filters) => (v: any) => setF((cur) => ({ ...cur, [k]: v, ...(k === 'city' ? { area: null } : {}) }));
  const city = cities.find((c) => c.id === f.city);
  const activeCount = [f.category, f.city, f.min_price, f.max_price, f.min_rating, f.max_prep_days, f.offer_type, f.available || null, f.delivery || null].filter(Boolean).length;
  const toggleCompare = (id: number) => setCompare((c) => (c.includes(id) ? c.filter((x) => x !== id) : c.length >= 4 ? c : [...c, id]));

  return (
    <View style={{ flex: 1 }}>
      <Screen>
        <Field value={f.q} onChangeText={set('q')} placeholder="كلمات البحث: شال مطرز، كعك، رسم…" returnKeyType="search" />
        <Row style={{ justifyContent: 'space-between' }}>
          <Pressable onPress={() => setShowFilters(!showFilters)}>
            <Row gap={4}>
              <Ionicons name="options-outline" size={20} color={colors.primary} />
              <T weight="semibold" color={colors.primary}>الفلاتر {activeCount ? `(${activeCount})` : ''}</T>
            </Row>
          </Pressable>
          <Pressable onPress={() => navigation.navigate('SmartSearch', { target: 'offers', text: f.q })}>
            <Row gap={4}>
              <Ionicons name="sparkles-outline" size={18} color={colors.gold} />
              <T weight="semibold" color={colors.gold}>جرّب المساعد الذكي</T>
            </Row>
          </Pressable>
        </Row>
        {showFilters ? (
          <Card>
            <Select label="التصنيف" allowNone options={offerCategories.map((c) => ({ value: c.id, label: c.name }))} value={f.category} onChange={set('category')} placeholder="كل التصنيفات" />
            <Select label="المدينة" allowNone options={cities.map((c) => ({ value: c.id, label: c.name }))} value={f.city} onChange={set('city')} placeholder="كل المدن" />
            {city ? <Select label="المنطقة" allowNone options={city.areas.map((a) => ({ value: a.id, label: a.name }))} value={f.area} onChange={set('area')} placeholder="كل المناطق" /> : null}
            <Row>
              <View style={{ flex: 1 }}><Field label="أقل سعر ₪" value={f.min_price} onChangeText={set('min_price')} keyboardType="numeric" /></View>
              <View style={{ flex: 1 }}><Field label="أعلى سعر ₪" value={f.max_price} onChangeText={set('max_price')} keyboardType="numeric" /></View>
            </Row>
            <Field label="أقصى مدة تجهيز (أيام)" value={f.max_prep_days} onChangeText={set('max_prep_days')} keyboardType="numeric" />
            <T weight="semibold" size={14}>نوع العرض</T>
            <Chips allowNone options={OFFER_TYPES} value={f.offer_type} onChange={set('offer_type')} />
            <T weight="semibold" size={14}>أقل تقييم</T>
            <Chips allowNone options={[3, 4, 4.5].map((r) => ({ value: r, label: `${r}★ فأعلى` }))} value={f.min_rating} onChange={set('min_rating')} />
            <Toggle label="المتاح الآن فقط" value={f.available} onChange={set('available')} />
            <Toggle label="يوفر التوصيل" value={f.delivery} onChange={set('delivery')} />
            <Button title="مسح الفلاتر" variant="ghost" small onPress={() => setF({ ...EMPTY, q: f.q })} />
          </Card>
        ) : null}
        <Chips options={ORDERING} value={f.ordering} onChange={(v) => set('ordering')(v ?? 'newest')} />
        {!loading || page > 1 ? <T size={13} color={colors.muted}>{count} نتيجة</T> : null}
        {error ? <ErrorView message={error} onRetry={() => run(1)} /> : null}
        {loading && page === 1 ? <Loading text="جارٍ البحث…" /> : !error && !items.length ? (
          <Empty icon="search-outline" title="لا توجد نتائج" subtitle="جرّب كلمات أخرى أو خفّف الفلاتر، أو استخدم المساعد الذكي." />
        ) : (
          items.map((o) => <OfferCard key={o.id} offer={o} onToggleCompare={() => toggleCompare(o.id)} inCompare={compare.includes(o.id)} />)
        )}
        {hasNext ? <Button title="عرض المزيد" variant="outline" loading={loading} onPress={() => run(page + 1)} /> : null}
      </Screen>
      {compare.length ? (
        <View style={{ position: 'absolute', bottom: 12, left: 12, right: 12, alignItems: 'center' }}>
          <View style={{ backgroundColor: colors.primaryDark, borderRadius: radius.lg, padding: space.sm, flexDirection: 'row', gap: space.sm, alignItems: 'center', maxWidth: 560, width: '100%' }}>
            <T color="#fff" style={{ flex: 1 }} size={13}>اخترت {compare.length} للمقارنة (حتى 4)</T>
            <Button small variant="gold" title="قارن" disabled={compare.length < 2} onPress={() => navigation.navigate('Compare', { kind: 'offers', ids: compare })} />
            <Button small variant="secondary" title="مسح" onPress={() => setCompare([])} />
          </View>
        </View>
      ) : null}
    </View>
  );
}
