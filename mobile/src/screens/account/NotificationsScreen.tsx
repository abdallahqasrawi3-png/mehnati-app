import React from 'react';
import { View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../api/client';
import { Paged } from '../../api/types';
import { useApi } from '../../hooks';
import { colors, dateTimeText } from '../../theme';
import { Button, Card, Empty, ErrorView, Loading, Row, Screen, T } from '../../ui';

type N = { id: number; kind: string; title: string; body: string; ref_type: string; ref_id: number | null; is_read: boolean; created_at: string };
const ICONS: Record<string, any> = { new_order: 'receipt-outline', order_status: 'swap-horizontal-outline', low_stock: 'warning-outline', shipment: 'car-outline', review: 'star-outline' };

export default function NotificationsScreen({ navigation }: any) {
  const { data, error, loading, reload } = useApi<Paged<N>>('/notifications/');
  const open = async (n: N) => {
    if (!n.is_read) api(`/notifications/${n.id}/read/`, { method: 'POST' }).catch(() => {});
    if (n.ref_type === 'sales_order') navigation.navigate('Order', { kind: 'sales', id: n.ref_id });
    else if (n.ref_type === 'purchase_order') navigation.navigate('Order', { kind: 'purchase', id: n.ref_id });
    else if (n.ref_type === 'shipment') navigation.navigate('Shipment', { id: n.ref_id });
    else if (n.ref_type === 'offer') navigation.navigate('OfferEdit', { id: n.ref_id });
    else if (n.ref_type === 'material') navigation.navigate('MaterialEdit', { id: n.ref_id });
    reload();
  };
  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <Button small variant="ghost" title="تعليم الكل كمقروء" icon="checkmark-done-outline" onPress={async () => { await api('/notifications/read_all/', { method: 'POST' }); reload(); }} />
      {loading && !data ? <Loading /> : error ? <ErrorView message={error} onRetry={reload} /> : !data?.results.length ? (
        <Empty icon="notifications-off-outline" title="لا توجد إشعارات" />
      ) : data.results.map((n) => (
        <Card key={n.id} onPress={() => open(n)} style={!n.is_read ? { borderColor: colors.gold, borderWidth: 1.5 } : null}>
          <Row style={{ alignItems: 'flex-start' }}>
            <Ionicons name={ICONS[n.kind] ?? 'notifications-outline'} size={22} color={colors.primary} />
            <View style={{ flex: 1 }}>
              <T weight={n.is_read ? 'regular' : 'bold'}>{n.title}</T>
              {n.body ? <T size={13} color={colors.muted}>{n.body}</T> : null}
              <T size={11} color={colors.muted}>{dateTimeText(n.created_at)}</T>
            </View>
          </Row>
        </Card>
      ))}
    </Screen>
  );
}
