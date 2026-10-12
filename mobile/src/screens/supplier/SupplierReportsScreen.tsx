import React, { useState } from 'react';
import { View } from 'react-native';
import { StatTile } from '../../charts';
import { useApi } from '../../hooks';
import { colors, dateText, money, qty, space } from '../../theme';
import { Card, Chips, ErrorView, KV, Loading, Screen, SectionTitle, T } from '../../ui';

export default function SupplierReportsScreen() {
  const [period, setPeriod] = useState('month');
  const { data: r, error, loading, reload } = useApi<any>('/reports/supplier/', { period });
  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <Chips options={[{ value: 'day', label: 'اليوم' }, { value: 'week', label: 'الأسبوع' }, { value: 'month', label: 'الشهر' }]} value={period} onChange={(v) => v && setPeriod(v)} />
      {loading && !r ? <Loading /> : error ? <ErrorView message={error} onRetry={reload} /> : r ? (
        <>
          <T size={13} color={colors.muted}>{r.period.label}: {dateText(r.period.start)} – {dateText(r.period.end)}</T>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
            <StatTile label="مبيعات مكتملة (مستلمة)" value={r.revenue} note={`${r.completed_orders} طلب`} emphasis />
            <StatTile label="مشحونة بانتظار التأكيد" value={r.shipped_awaiting_confirmation.total} note={`${r.shipped_awaiting_confirmation.orders} طلب`} />
          </View>
          <Card>
            <KV k="طلبات مفتوحة" v={String(r.open_orders)} />
            <KV k="مواد بمخزون منخفض" v={String(r.low_stock_items)} />
          </Card>
          <SectionTitle title="الأكثر مبيعًا" />
          <Card>
            {r.best_materials.length ? r.best_materials.map((b: any) => (
              <KV key={b.title} k={b.title} v={`${qty(b.quantity)} ${b.unit} · ${money(b.revenue)}`} />
            )) : <T color={colors.muted}>لا يوجد بعد.</T>}
          </Card>
          {r.notes.map((n: string) => <T key={n} size={12} color={colors.muted}>• {n}</T>)}
        </>
      ) : null}
    </Screen>
  );
}
