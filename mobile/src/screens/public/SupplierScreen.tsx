import React from 'react';
import { Linking } from 'react-native';
import { Material, Paged } from '../../api/types';
import { MaterialCard } from '../../components';
import { useApi } from '../../hooks';
import ReportAbuse from '../../ReportAbuse';
import { colors, money } from '../../theme';
import { Button, Card, Empty, ErrorView, KV, Loading, Screen, SectionTitle, T } from '../../ui';

export default function SupplierScreen({ route }: any) {
  const id = route.params.id;
  const s = useApi<any>(`/suppliers/${id}/`);
  const mats = useApi<Paged<Material>>('/materials/', { supplier: id });
  if (s.loading && !s.data) return <Screen><Loading /></Screen>;
  if (s.error || !s.data) return <Screen><ErrorView message={s.error ?? ''} onRetry={s.reload} /></Screen>;
  const x = s.data;
  return (
    <Screen>
      <Card>
        <T weight="bold" size={20}>{x.name}</T>
        <T color={colors.muted}>{x.city_name}{x.area_name ? ` - ${x.area_name}` : ''}</T>
        {x.description ? <T>{x.description}</T> : null}
        <KV k="الاستلام" v={x.pickup_available ? 'متاح' : 'غير متاح'} />
        <KV k="التوصيل" v={x.delivery_available ? `خلال ${x.delivery_days ?? '؟'} يوم` : 'غير متاح'} />
        <KV k="تكلفة التوصيل التقديرية" v={x.delivery_cost ? money(x.delivery_cost) : 'غير محددة'} />
        {x.public_phone ? <Button small variant="outline" icon="call-outline" title="اتصال" onPress={() => Linking.openURL(`tel:${x.public_phone}`)} /> : null}
      </Card>
      <SectionTitle title={`المواد (${x.materials_count})`} />
      {mats.loading ? <Loading /> : !mats.data?.results.length ? <Empty title="لا توجد مواد" /> : mats.data.results.map((m) => <MaterialCard key={m.id} m={m} />)}
      <ReportAbuse type="supplier" id={x.id} />
    </Screen>
  );
}
