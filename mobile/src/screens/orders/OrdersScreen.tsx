import React, { useState } from 'react';
import { Paged } from '../../api/types';
import { StatusBadge } from '../../components';
import { useApi } from '../../hooks';
import { colors, dateText, money } from '../../theme';
import { Card, Chips, Empty, ErrorView, Loading, Row, Screen, T } from '../../ui';

const TITLES: Record<string, string> = {
  'sales:customer': 'طلباتي', 'sales:business': 'طلبات العملاء', 'purchase:buyer': 'مشترياتي من الموردين', 'purchase:supplier': 'طلبات الشراء الواردة',
};

const OPEN = { sales: 'pending,accepted,preparing,ready,in_transit,delivery_failed', purchase: 'pending,accepted,preparing,shipped' };
const DONE = { sales: 'completed,rejected,cancelled', purchase: 'received,rejected,cancelled' };

export default function OrdersScreen({ route, navigation }: any) {
  const { kind, role } = route.params as { kind: 'sales' | 'purchase'; role: string };
  const [filter, setFilter] = useState<'open' | 'done' | 'all'>('open');
  React.useLayoutEffect(() => navigation.setOptions({ title: TITLES[`${kind}:${role}`] ?? 'الطلبات' }), [navigation, kind, role]);
  const status = filter === 'open' ? OPEN[kind] : filter === 'done' ? DONE[kind] : undefined;
  const { data, error, loading, reload } = useApi<Paged<any>>(kind === 'sales' ? '/sales-orders/' : '/purchase-orders/', { role, status });

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <Chips options={[{ value: 'open', label: 'الجارية' }, { value: 'done', label: 'المنتهية' }, { value: 'all', label: 'الكل' }]} value={filter} onChange={(v) => v && setFilter(v as any)} />
      {loading && !data ? <Loading /> : error ? <ErrorView message={error} onRetry={reload} /> : !data?.results.length ? (
        <Empty icon="receipt-outline" title="لا توجد طلبات هنا" />
      ) : data.results.map((o) => (
        <Card key={o.id} onPress={() => navigation.navigate('Order', { kind, id: o.id })}>
          <Row style={{ justifyContent: 'space-between' }}>
            <T weight="bold">طلب #{o.id}</T>
            <StatusBadge status={o.status} label={o.status_display} />
          </Row>
          <T size={13} color={colors.muted}>
            {kind === 'sales'
              ? role === 'business' ? `العميل: ${o.customer_name}` : `من: ${o.business_name}`
              : role === 'supplier' ? `المشتري: ${o.business_name}` : `المورد: ${o.supplier_name}`}
          </T>
          <Row style={{ justifyContent: 'space-between' }}>
            <T size={13} color={colors.muted}>{o.items_count} عنصر · {o.fulfillment === 'delivery' ? 'توصيل' : 'استلام'} · {dateText(o.created_at)}</T>
            <T weight="bold" color={colors.primary}>{money(o.total)}</T>
          </Row>
        </Card>
      ))}
    </Screen>
  );
}
