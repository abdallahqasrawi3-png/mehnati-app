import React from 'react';
import { Linking, ScrollView, View } from 'react-native';
import { imageUrl } from '../../api/client';
import { Img, Offer, Paged } from '../../api/types';
import { OfferCard } from '../../components';
import { useApi } from '../../hooks';
import ReportAbuse from '../../ReportAbuse';
import { colors, dateText, space } from '../../theme';
import { Badge, Button, Card, Empty, ErrorView, KV, Loading, Notice, Row, Screen, SectionTitle, Stars, T, Thumb } from '../../ui';

type Business = {
  id: number; name: string; description: string; category: { name: string }; city_name: string; area_name: string | null;
  public_phone: string | null; public_whatsapp: string | null; working_hours: string; pickup_available: boolean;
  delivery_available: boolean; rating_avg: string; rating_count: number; logo: string | null; work_images: Img[]; offers_count: number;
};
type Review = { id: number; rating: number; comment: string; customer_name: string; items: string[]; created_at: string };

export default function BusinessScreen({ route }: any) {
  const id = route.params.id;
  const b = useApi<Business>(`/businesses/${id}/`);
  const offers = useApi<Paged<Offer>>('/offers/', { business: id });
  const reviews = useApi<Paged<Review>>('/reviews/', { business: id });

  if (b.loading && !b.data) return <Screen><Loading /></Screen>;
  if (b.error || !b.data) return <Screen><ErrorView message={b.error ?? 'غير موجود'} onRetry={b.reload} /></Screen>;
  const x = b.data;
  const wa = x.public_whatsapp?.replace(/[^0-9]/g, '');

  return (
    <Screen refreshing={b.loading} onRefresh={() => { b.reload(); offers.reload(); reviews.reload(); }}>
      <Card style={{ alignItems: 'center' }}>
        <Thumb uri={imageUrl(x.logo) ?? imageUrl(x.work_images[0]?.image)} size={84} style={{ borderRadius: 42 }} />
        <T weight="bold" size={20} center>{x.name}</T>
        <Row wrap gap={6} style={{ justifyContent: 'center' }}>
          <Badge text={x.category.name} tone="primary" />
          <Badge text={`${x.city_name}${x.area_name ? ' - ' + x.area_name : ''}`} />
        </Row>
        <Stars value={x.rating_avg} count={x.rating_count} size={16} />
        {x.description ? <T center color={colors.muted}>{x.description}</T> : null}
      </Card>
      <Card>
        <KV k="ساعات العمل" v={x.working_hours || 'غير محددة'} />
        <KV k="الاستلام والتوصيل" v={[x.pickup_available && 'استلام', x.delivery_available && 'توصيل'].filter(Boolean).join(' / ')} />
        <KV k="عدد العروض" v={String(x.offers_count)} />
        {x.public_phone || wa ? (
          <Row wrap>
            {x.public_phone ? <Button small title="اتصال" icon="call-outline" variant="outline" onPress={() => Linking.openURL(`tel:${x.public_phone}`)} /> : null}
            {wa ? <Button small title="واتساب" icon="logo-whatsapp" variant="outline" onPress={() => Linking.openURL(`https://wa.me/${wa.startsWith('0') ? '970' + wa.slice(1) : wa}`)} /> : null}
          </Row>
        ) : (
          <Notice text="لم يوافق صاحب المشروع على نشر وسائل التواصل. يمكنك الطلب عبر التطبيق مباشرة." />
        )}
        <T size={12} color={colors.muted}>يظهر الموقع العام فقط (المدينة/المنطقة) لحماية خصوصية صاحب المشروع.</T>
      </Card>
      {x.work_images.length ? (
        <>
          <SectionTitle title="صور الأعمال" />
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.sm }}>
            {x.work_images.map((img) => <Thumb key={img.id} uri={imageUrl(img.image)} size={120} />)}
          </ScrollView>
        </>
      ) : null}
      <SectionTitle title="المنتجات والخدمات" />
      {offers.loading ? <Loading /> : !offers.data?.results.length ? <Empty title="لا توجد عروض حاليًا" /> :
        offers.data.results.map((o) => <OfferCard key={o.id} offer={o} compact />)}
      <SectionTitle title={`التقييمات (${x.rating_count})`} />
      {reviews.loading ? <Loading /> : !reviews.data?.results.length ? <Empty icon="star-outline" title="لا توجد تقييمات بعد" subtitle="التقييمات تأتي فقط من عملاء أكملوا طلباتهم." /> :
        reviews.data.results.map((r) => (
          <Card key={r.id}>
            <Row style={{ justifyContent: 'space-between' }}>
              <T weight="semibold">{r.customer_name}</T>
              <Stars value={r.rating} />
            </Row>
            {r.comment ? <T>{r.comment}</T> : null}
            <T size={12} color={colors.muted}>{r.items.join('، ')} · {dateText(r.created_at)}</T>
            <View style={{ alignItems: 'flex-start' }}><ReportAbuse type="review" id={r.id} /></View>
          </Card>
        ))}
      <ReportAbuse type="business" id={x.id} />
    </Screen>
  );
}
