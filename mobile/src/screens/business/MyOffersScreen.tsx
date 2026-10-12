import React from 'react';
import { View } from 'react-native';
import { imageUrl } from '../../api/client';
import { Paged } from '../../api/types';
import { offerTypeTone } from '../../components';
import { useApi } from '../../hooks';
import { colors, money } from '../../theme';
import { Badge, Button, Card, Empty, ErrorView, Loading, Row, Screen, T, Thumb } from '../../ui';

export default function MyOffersScreen({ navigation }: any) {
  const { data, error, loading, reload } = useApi<Paged<any>>('/my/offers/');
  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <Button title="إضافة منتج أو خدمة" icon="add-circle-outline" onPress={() => navigation.navigate('OfferEdit', {})} />
      {loading && !data ? <Loading /> : error ? <ErrorView message={error} onRetry={reload} /> : !data?.results.length ? (
        <Empty icon="pricetags-outline" title="لم تضف عروضًا بعد" subtitle="أضف منتجًا جاهزًا بكمية، أو منتجًا حسب الطلب، أو خدمة." />
      ) : data.results.map((o) => {
        const low = o.offer_type === 'ready' && o.low_stock_threshold > 0 && o.available_quantity <= o.low_stock_threshold;
        return (
          <Card key={o.id} onPress={() => navigation.navigate('OfferEdit', { id: o.id })}>
            <Row style={{ alignItems: 'flex-start' }}>
              <Thumb uri={imageUrl(o.images[0]?.image)} size={64} />
              <View style={{ flex: 1, gap: 2 }}>
                <T weight="bold">{o.title}</T>
                <Row wrap gap={6}>
                  <Badge text={o.offer_type_display} tone={offerTypeTone(o.offer_type) as any} />
                  {!o.is_available ? <Badge text="موقوف" tone="danger" /> : null}
                  {low ? <Badge text="مخزون منخفض" tone="warning" /> : null}
                </Row>
                <T size={13} color={colors.muted}>
                  {money(o.price)} {o.price_unit}
                  {o.offer_type === 'ready' ? ` · المخزون ${o.stock_quantity} (محجوز ${o.reserved_quantity})` : ''}
                </T>
              </View>
            </Row>
          </Card>
        );
      })}
    </Screen>
  );
}
