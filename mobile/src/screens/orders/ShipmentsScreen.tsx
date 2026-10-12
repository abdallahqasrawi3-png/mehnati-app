import React from 'react';
import { Paged } from '../../api/types';
import { StatusBadge } from '../../components';
import { useApi } from '../../hooks';
import { colors, dateTimeText } from '../../theme';
import { Card, Empty, ErrorView, Loading, Row, Screen, T } from '../../ui';

export default function ShipmentsScreen({ navigation }: any) {
  const { data, error, loading, reload } = useApi<Paged<any>>('/shipments/');
  return (
    <Screen refreshing={loading} onRefresh={reload}>
      {loading && !data ? <Loading /> : error ? <ErrorView message={error} onRetry={reload} /> : !data?.results.length ? (
        <Empty icon="car-outline" title="لا توجد شحنات" subtitle="تظهر هنا شحنات طلباتك المرسلة أو الواردة." />
      ) : data.results.map((s) => (
        <Card key={s.id} onPress={() => navigation.navigate('Shipment', { id: s.id })}>
          <Row style={{ justifyContent: 'space-between' }}>
            <T weight="bold">شحنة #{s.id} · طلب #{s.order_id}</T>
            <StatusBadge status={s.status} label={s.status_display} />
          </Row>
          <T size={13} color={colors.muted}>{s.kind_display} · {s.carrier_display}{s.tracking_number ? ` · ${s.tracking_number}` : ''}</T>
          <T size={12} color={colors.muted}>{s.my_role === 'sender' ? 'أنت المرسل' : 'أنت المستلم'} · آخر تحديث {dateTimeText(s.last_update)}</T>
        </Card>
      ))}
    </Screen>
  );
}
