import React from 'react';
import { ScrollView, View } from 'react-native';
import { imageUrl } from '../../api/client';
import { prepText } from '../../components';
import { useApi } from '../../hooks';
import { colors, money, qty, radius, space } from '../../theme';
import { Button, ErrorView, Loading, Notice, Screen, Stars, T, Thumb } from '../../ui';

/** Side-by-side comparison of offers or raw materials with clear units. */
export default function CompareScreen({ route, navigation }: any) {
  const { kind = 'offers', ids = [] } = (route.params ?? {}) as { kind?: 'offers' | 'materials'; ids?: number[] | string };
  const idList = Array.isArray(ids) ? ids.join(',') : String(ids);
  const { data, error, loading, reload } = useApi<any>(`/${kind}/compare/`, { ids: idList });
  if (loading) return <Screen><Loading /></Screen>;
  if (error || !data) return <Screen><ErrorView message={error ?? ''} onRetry={reload} /></Screen>;
  const items: any[] = kind === 'offers' ? data.offers : data.materials;

  const rows: [string, (x: any) => React.ReactNode][] = kind === 'offers'
    ? [
        ['السعر', (x) => <T weight="bold" color={colors.primary}>{money(x.price)}</T>],
        ['وحدة السعر', (x) => x.price_unit],
        ['النوع', (x) => x.offer_type_display],
        ['التجهيز', (x) => prepText(x.preparation_days)],
        ['المتاح', (x) => (x.available_quantity ?? 'حسب الطلب')],
        ['المشروع', (x) => x.business.name],
        ['المدينة', (x) => x.business.city_name],
        ['التقييم', (x) => <Stars value={x.business.rating_avg} count={x.business.rating_count} />],
        ['التوصيل', (x) => (x.business.delivery_available ? 'متوفر' : 'استلام فقط')],
      ]
    : [
        ['سعر الوحدة', (x) => <T weight="bold" color={colors.primary}>{money(x.price)}</T>],
        ['الوحدة', (x) => x.unit_display],
        ['المواصفات', (x) => x.specifications || '—'],
        ['المتاح', (x) => `${qty(x.available_quantity)} ${x.unit_display}`],
        ['الحد الأدنى', (x) => `${qty(x.min_order_quantity)} ${x.unit_display}`],
        ['المورد', (x) => x.supplier.name],
        ['الموقع', (x) => x.supplier.city_name],
        ['التوصيل', (x) => (x.supplier.delivery_available ? `${x.supplier.delivery_days ?? '؟'} يوم` : 'استلام فقط')],
        ['تكلفة التوصيل', (x) => (x.supplier.delivery_cost ? `${money(x.supplier.delivery_cost)} (تقديرية)` : 'غير محددة')],
      ];

  const colW = 170;
  return (
    <Screen>
      {data.note ? <Notice tone="warning" text={data.note} /> : <Notice tone="success" text="جميع العناصر بنفس وحدة السعر، المقارنة مباشرة." />}
      <ScrollView horizontal>
        <View style={{ borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, backgroundColor: colors.card }}>
          <View style={{ flexDirection: 'row' }}>
            <View style={{ width: 110 }} />
            {items.map((x) => (
              <View key={x.id} style={{ width: colW, padding: space.sm, alignItems: 'center', gap: 4 }}>
                <Thumb uri={imageUrl(x.images[0]?.image)} size={70} />
                <T weight="bold" size={13} center numberOfLines={2}>{x.title}</T>
                <Button small variant="outline" title="عرض" onPress={() => navigation.navigate(kind === 'offers' ? 'Offer' : 'Material', { id: x.id })} />
              </View>
            ))}
          </View>
          {rows.map(([label, fn], i) => (
            <View key={label} style={{ flexDirection: 'row', backgroundColor: i % 2 ? colors.card : colors.bg }}>
              <View style={{ width: 110, padding: space.sm, justifyContent: 'center' }}><T size={13} color={colors.muted}>{label}</T></View>
              {items.map((x) => {
                const v = fn(x);
                return (
                  <View key={x.id} style={{ width: colW, padding: space.sm, alignItems: 'center', justifyContent: 'center' }}>
                    {typeof v === 'string' || typeof v === 'number' ? <T size={13} center>{String(v)}</T> : v}
                  </View>
                );
              })}
            </View>
          ))}
        </View>
      </ScrollView>
    </Screen>
  );
}
