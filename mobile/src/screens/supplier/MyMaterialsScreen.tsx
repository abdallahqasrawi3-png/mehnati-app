import React from 'react';
import { View } from 'react-native';
import { imageUrl } from '../../api/client';
import { Paged } from '../../api/types';
import { useApi } from '../../hooks';
import { colors, money, qty } from '../../theme';
import { Badge, Button, Card, Empty, ErrorView, Loading, Row, Screen, T, Thumb } from '../../ui';

export default function MyMaterialsScreen({ navigation }: any) {
  const { data, error, loading, reload } = useApi<Paged<any>>('/my/materials/');
  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <Button title="إضافة مادة خام" icon="add-circle-outline" onPress={() => navigation.navigate('MaterialEdit', {})} />
      {loading && !data ? <Loading /> : error ? <ErrorView message={error} onRetry={reload} /> : !data?.results.length ? (
        <Empty icon="layers-outline" title="لا توجد مواد بعد" />
      ) : data.results.map((m) => {
        const low = Number(m.low_stock_threshold) > 0 && Number(m.available_quantity) <= Number(m.low_stock_threshold);
        return (
          <Card key={m.id} onPress={() => navigation.navigate('MaterialEdit', { id: m.id })}>
            <Row style={{ alignItems: 'flex-start' }}>
              <Thumb uri={imageUrl(m.images[0]?.image)} size={64} />
              <View style={{ flex: 1, gap: 2 }}>
                <T weight="bold">{m.title}</T>
                <Row wrap gap={6}>
                  {!m.is_available ? <Badge text="موقوفة" tone="danger" /> : null}
                  {low ? <Badge text="مخزون منخفض" tone="warning" /> : null}
                </Row>
                <T size={13} color={colors.muted}>
                  {money(m.price)} / {m.unit_display} · المتاح {qty(m.available_quantity)} (محجوز {qty(m.reserved_quantity)})
                </T>
              </View>
            </Row>
          </Card>
        );
      })}
    </Screen>
  );
}
