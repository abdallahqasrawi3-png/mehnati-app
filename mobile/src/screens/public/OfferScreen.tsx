import React, { useState } from 'react';
import { View } from 'react-native';
import { Offer } from '../../api/types';
import { useAuth } from '../../auth';
import { useCart } from '../../cart';
import { Gallery, offerTypeTone, prepText, QtyStepper } from '../../components';
import { useToast } from '../../feedback';
import { useApi } from '../../hooks';
import ReportAbuse from '../../ReportAbuse';
import { colors, money, space } from '../../theme';
import { Badge, Button, Card, ErrorView, KV, Loading, Notice, Row, Screen, Stars, T } from '../../ui';

export default function OfferScreen({ route, navigation }: any) {
  const { data: o, error, loading, reload } = useApi<Offer>(`/offers/${route.params.id}/`);
  const { me } = useAuth();
  const cart = useCart();
  const toast = useToast();
  const [q, setQ] = useState(1);

  if (loading && !o) return <Screen><Loading /></Screen>;
  if (error || !o) return <Screen><ErrorView message={error ?? 'غير موجود'} onRetry={reload} /></Screen>;

  const own = me?.business_profile_id === o.business.id;
  const maxQ = o.available_quantity ?? 99;
  const add = () => {
    const { replaced } = cart.addOffer(o, q);
    toast(replaced ? 'أُفرغت السلة السابقة لأن الطلب يكون من مشروع واحد، وأضيف العرض.' : 'أضيف إلى السلة.', replaced ? 'info' : 'success');
  };

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <Gallery images={o.images} />
      <View style={{ gap: 4 }}>
        <Row wrap gap={6}>
          <Badge text={o.offer_type_display} tone={offerTypeTone(o.offer_type) as any} />
          <Badge text={o.category.name} />
          {!o.is_orderable ? <Badge text="غير متاح حاليًا" tone="danger" /> : null}
        </Row>
        <T weight="bold" size={22}>{o.title}</T>
        <T weight="bold" size={22} color={colors.primary}>{money(o.price)} <T color={colors.muted} size={14}>{o.price_unit}</T></T>
      </View>
      <Card>
        <KV k="مدة التجهيز" v={prepText(o.preparation_days)} />
        {o.service_duration ? <KV k="مدة تنفيذ الخدمة" v={o.service_duration} /> : null}
        {o.available_quantity !== null ? <KV k="الكمية المتاحة" v={String(o.available_quantity)} /> : <KV k="المخزون" v={o.offer_type === 'service' ? 'خدمة بموعد' : 'يُصنع حسب الطلب'} />}
        <KV k="الاستلام" v={[o.business.pickup_available && 'استلام', o.business.delivery_available && 'توصيل'].filter(Boolean).join(' / ')} />
      </Card>
      {o.description ? <Card><T weight="semibold">الوصف</T><T>{o.description}</T></Card> : null}
      <Card onPress={() => navigation.navigate('Business', { id: o.business.id })}>
        <T size={13} color={colors.muted}>صاحب المشروع</T>
        <Row style={{ justifyContent: 'space-between' }}>
          <T weight="bold">{o.business.name}</T>
          <Stars value={o.business.rating_avg} count={o.business.rating_count} />
        </Row>
        <T size={13} color={colors.muted}>{o.business.city_name}{o.business.area_name ? ` - ${o.business.area_name}` : ''} · اضغط لعرض الصفحة والتواصل</T>
      </Card>
      {own ? (
        <Notice text="هذا عرض من مشروعك. يمكنك تعديله من «منتجاتي وخدماتي»." />
      ) : o.is_orderable ? (
        <Card style={{ gap: space.md }}>
          <Row style={{ justifyContent: 'space-between' }}>
            <T weight="semibold">الكمية</T>
            <QtyStepper value={q} onChange={setQ} max={maxQ} />
          </Row>
          <T color={colors.muted} size={13}>المجموع التقديري: {money(Number(o.price) * q)} (يُحسب النهائي عند إنشاء الطلب)</T>
          <Button title="أضف إلى السلة" icon="bag-add-outline" onPress={add} />
          <Notice text="الدفع يتم مباشرة مع صاحب المشروع عند الاستلام؛ لا يوجد دفع إلكتروني داخل التطبيق." />
        </Card>
      ) : (
        <Button title="غير متاح للطلب حاليًا" disabled disabledReason="نفدت الكمية أو أوقف صاحب المشروع العرض مؤقتًا." />
      )}
      <ReportAbuse type="offer" id={o.id} />
    </Screen>
  );
}
