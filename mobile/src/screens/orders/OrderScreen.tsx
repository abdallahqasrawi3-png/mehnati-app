import React, { useState } from 'react';
import { Linking, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api, ApiError } from '../../api/client';
import { StatusBadge } from '../../components';
import { confirm, useToast } from '../../feedback';
import { useApi } from '../../hooks';
import { colors, dateText, dateTimeText, money, qty, space } from '../../theme';
import { Button, Card, Chips, ErrorView, Field, KV, Loading, Notice, Row, Screen, SectionTitle, Stars, T, Toggle } from '../../ui';

const ACTION_LABELS: Record<string, { label: string; variant: any; icon: any }> = {
  accepted: { label: 'قبول الطلب', variant: 'primary', icon: 'checkmark-circle-outline' },
  rejected: { label: 'رفض الطلب', variant: 'danger', icon: 'close-circle-outline' },
  cancelled: { label: 'إلغاء الطلب', variant: 'danger', icon: 'trash-outline' },
  preparing: { label: 'بدء التجهيز', variant: 'primary', icon: 'construct-outline' },
  ready: { label: 'جاهز للاستلام/الشحن', variant: 'primary', icon: 'cube-outline' },
  in_transit: { label: 'خرج للتوصيل', variant: 'gold', icon: 'car-outline' },
  completed: { label: 'تم التسليم (إكمال الطلب)', variant: 'primary', icon: 'checkmark-done-outline' },
  delivery_failed: { label: 'تعذّر التسليم', variant: 'outline', icon: 'alert-circle-outline' },
  shipped: { label: 'تم الشحن / جاهز للاستلام', variant: 'gold', icon: 'car-outline' },
  received: { label: 'تأكيد استلام المواد', variant: 'primary', icon: 'checkmark-done-outline' },
};

const LOG_NAMES: Record<string, string> = {
  pending: 'إنشاء الطلب', accepted: 'قبول', rejected: 'رفض', cancelled: 'إلغاء', preparing: 'قيد التجهيز',
  ready: 'جاهز', in_transit: 'في الطريق', completed: 'مكتمل', delivery_failed: 'تعذر التسليم',
  shipped: 'مشحون / جاهز للاستلام', received: 'تم الاستلام',
};

function ReviewForm({ orderId, onDone }: { orderId: number; onDone: () => void }) {
  const toast = useToast();
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState('');
  const send = async () => {
    try {
      await api('/reviews/', { method: 'POST', body: { order: orderId, rating, comment } });
      toast('شكرًا لتقييمك!');
      onDone();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر إرسال التقييم', 'error');
    }
  };
  return (
    <Card>
      <T weight="bold">قيّم تجربتك</T>
      <Row>
        {[1, 2, 3, 4, 5].map((n) => (
          <Ionicons key={n} name={n <= rating ? 'star' : 'star-outline'} size={32} color={colors.gold} onPress={() => setRating(n)} accessibilityLabel={`${n} نجوم`} />
        ))}
      </Row>
      <Field multiline value={comment} onChangeText={setComment} placeholder="اكتب رأيك في المنتج والتعامل (اختياري)" />
      <Button title="إرسال التقييم" onPress={send} />
    </Card>
  );
}

function DeliveryTerms({ order, path, onDone }: { order: any; path: string; onDone: (o: any) => void }) {
  const toast = useToast();
  const [fee, setFee] = useState(order.delivery_fee ?? '');
  const [payer, setPayer] = useState(order.delivery_payer);
  const [final, setFinal] = useState(order.delivery_fee_is_final);
  const save = async () => {
    try {
      const o = await api(`${path}delivery/`, { method: 'POST', body: { delivery_fee: fee === '' ? null : fee, delivery_payer: payer, delivery_fee_is_final: final } });
      toast('تم حفظ تكلفة التوصيل.');
      onDone(o);
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر الحفظ', 'error');
    }
  };
  return (
    <Card>
      <T weight="bold">تكلفة التوصيل</T>
      <Field label="التكلفة ₪" value={String(fee)} onChangeText={setFee} keyboardType="numeric" />
      <T size={14} weight="semibold">من يدفع التوصيل؟</T>
      <Chips options={[{ value: 'buyer', label: 'المشتري' }, { value: 'seller', label: 'البائع (على حسابي)' }]} value={payer} onChange={(v) => v && setPayer(v)} />
      <Toggle label="التكلفة نهائية (وليست تقديرية)" value={final} onChange={setFinal} />
      <Button title="حفظ" variant="outline" onPress={save} />
    </Card>
  );
}

function ShipmentForm({ kind, orderId, onDone }: { kind: string; orderId: number; onDone: () => void }) {
  const toast = useToast();
  const carriers = useApi<any[]>('/carriers/');
  const [carrierId, setCarrierId] = useState<number | null>(null);
  const [name, setName] = useState('');
  const [tracking, setTracking] = useState('');
  const [cost, setCost] = useState('');
  const [eta, setEta] = useState('');
  const save = async () => {
    try {
      await api('/shipments/', {
        method: 'POST',
        body: { kind, order_id: orderId, carrier_id: carrierId, carrier_name: name, tracking_number: tracking, cost: cost || null, estimated_arrival: eta || null },
      });
      toast('تم تسجيل الشحنة.');
      onDone();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر تسجيل الشحنة', 'error');
    }
  };
  return (
    <Card>
      <T weight="bold">تسجيل شحنة</T>
      <Notice text="سجّل بيانات شركة التوصيل يدويًا. الربط التلقائي مع شركات التوصيل يتطلب تكاملًا معتمدًا من الشركة." />
      {carriers.data?.length ? (
        <Chips allowNone options={carriers.data.map((c) => ({ value: c.id, label: c.name }))} value={carrierId} onChange={setCarrierId} />
      ) : null}
      {!carrierId ? <Field label="اسم شركة التوصيل" value={name} onChangeText={setName} /> : null}
      <Field label="رقم التتبع (إن وجد)" value={tracking} onChangeText={setTracking} />
      <Row>
        <View style={{ flex: 1 }}><Field label="التكلفة ₪" value={cost} onChangeText={setCost} keyboardType="numeric" /></View>
        <View style={{ flex: 1 }}><Field label="الوصول المتوقع" value={eta} onChangeText={setEta} placeholder="2026-10-20" /></View>
      </Row>
      <Button title="تسجيل الشحنة" icon="car-outline" onPress={save} disabled={!carrierId && !name.trim()} disabledReason="اكتب اسم شركة التوصيل" />
    </Card>
  );
}

export default function OrderScreen({ route, navigation }: any) {
  const { kind, id } = route.params as { kind: 'sales' | 'purchase'; id: number };
  const path = `/${kind === 'sales' ? 'sales-orders' : 'purchase-orders'}/${id}/`;
  const { data: o, error, loading, reload, setData } = useApi<any>(path);
  const toast = useToast();
  const [note, setNote] = useState('');

  if (loading && !o) return <Screen><Loading /></Screen>;
  if (error || !o) return <Screen><ErrorView message={error ?? ''} onRetry={reload} /></Screen>;

  const seller = o.my_role === 'seller';
  const finalStates = kind === 'sales' ? ['completed', 'rejected', 'cancelled'] : ['received', 'rejected', 'cancelled'];
  const shippable = kind === 'sales' ? ['accepted', 'preparing', 'ready', 'in_transit', 'delivery_failed'] : ['accepted', 'preparing', 'shipped'];

  const move = async (status: string) => {
    const a = ACTION_LABELS[status];
    if (!(await confirm(`${a?.label ?? status}؟`, 'سيتم إشعار الطرف الآخر بالتغيير.'))) return;
    try {
      setData(await api(`${path}transition/`, { method: 'POST', body: { status, note } }));
      setNote('');
      toast('تم تحديث حالة الطلب.');
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر التحديث', 'error');
    }
  };

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <Card>
        <Row style={{ justifyContent: 'space-between' }}>
          <T weight="bold" size={18}>{kind === 'sales' ? 'طلب' : 'طلب شراء'} #{o.id}</T>
          <StatusBadge status={o.status} label={o.status_display} />
        </Row>
        <T color={colors.muted} size={13}>{o.next_step}</T>
        {kind === 'sales' ? (
          <>
            <KV k="المشروع" v={o.business_name} />
            <KV k="العميل" v={o.customer_name} />
          </>
        ) : (
          <>
            <KV k="المورد" v={o.supplier_name} />
            <KV k="المشروع المشتري" v={o.business_name} />
          </>
        )}
        <KV k="تاريخ الطلب" v={dateTimeText(o.created_at)} />
        {o.requested_date ? <KV k="الموعد المطلوب" v={dateText(o.requested_date)} /> : null}
        {o.notes ? <KV k="ملاحظات" v={o.notes} /> : null}
      </Card>

      <SectionTitle title="العناصر" />
      <Card>
        {o.items.map((it: any) => (
          <Row key={it.id} style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <View style={{ flex: 1 }}>
              <T weight="semibold">{it.title}</T>
              <T size={12} color={colors.muted}>
                {qty(it.quantity)} {kind === 'purchase' ? it.unit_display : ''} × {money(it.unit_price)} {it.price_unit ?? ''}
              </T>
            </View>
            <T weight="semibold">{money(it.line_total)}</T>
          </Row>
        ))}
        <KV k="مجموع العناصر" v={money(o.subtotal)} />
        {o.fulfillment === 'delivery' ? (
          <KV k="التوصيل" v={o.delivery_fee === null ? 'لم تُحدد بعد' : `${money(o.delivery_fee)} · يدفعها ${o.delivery_payer === 'buyer' ? 'المشتري' : 'البائع'} · ${o.delivery_fee_is_final ? 'نهائية' : 'تقديرية'}`} />
        ) : null}
        <Row style={{ justifyContent: 'space-between' }}>
          <T weight="bold">الإجمالي على المشتري</T>
          <T weight="bold" size={18} color={colors.primary}>{money(o.total)}</T>
        </Row>
        <T size={12} color={colors.muted}>الأسعار محفوظة كما كانت وقت إنشاء الطلب. الدفع مباشرة مع البائع.</T>
      </Card>

      <Card>
        <T weight="bold">{o.fulfillment === 'delivery' ? 'التوصيل' : 'الاستلام'}</T>
        {o.fulfillment === 'delivery' ? (
          <>
            <T>{o.recipient_name} · {o.recipient_phone}</T>
            <T color={colors.muted}>{o.delivery_city}{o.delivery_area ? ` - ${o.delivery_area}` : ''} · {o.delivery_address}</T>
            {o.delivery_map_url ? (
              <Button small variant="outline" icon="map-outline" title="فتح موقع التسليم على الخريطة" onPress={() => Linking.openURL(o.delivery_map_url)} />
            ) : null}
            <T size={12} color={colors.muted}>هذه البيانات خاصة وتظهر لطرفي الطلب فقط.</T>
          </>
        ) : <T color={colors.muted}>استلام من البائع بالتنسيق معه.</T>}
        {o.shipment ? (
          <Button small variant="outline" icon="car-outline" title={`الشحنة: ${o.shipment.status_display}${o.shipment.tracking_number ? ' · ' + o.shipment.tracking_number : ''}`} onPress={() => navigation.navigate('Shipment', { id: o.shipment.id })} />
        ) : null}
      </Card>

      {o.allowed_next.length ? (
        <Card>
          <T weight="bold">الإجراءات المتاحة</T>
          <Field value={note} onChangeText={setNote} placeholder="ملاحظة مع التغيير (اختياري، مثل سبب الرفض)" />
          {o.allowed_next.map((s: any) => (
            <Button key={s.status} title={ACTION_LABELS[s.status]?.label ?? s.label} variant={ACTION_LABELS[s.status]?.variant ?? 'primary'} icon={ACTION_LABELS[s.status]?.icon} onPress={() => move(s.status)} />
          ))}
          {!seller && o.status !== 'pending' && kind === 'sales' ? <T size={12} color={colors.muted}>يمكن للعميل الإلغاء فقط قبل قبول الطلب.</T> : null}
        </Card>
      ) : !finalStates.includes(o.status) ? (
        <Notice text={seller ? 'لا يوجد إجراء متاح لك الآن.' : 'بانتظار تحديث البائع للطلب.'} />
      ) : null}

      {seller && o.fulfillment === 'delivery' && !finalStates.includes(o.status) ? (
        <DeliveryTerms order={o} path={path} onDone={setData} />
      ) : null}
      {seller && o.fulfillment === 'delivery' && !o.shipment && shippable.includes(o.status) ? (
        <ShipmentForm kind={kind} orderId={o.id} onDone={reload} />
      ) : null}

      {kind === 'sales' && o.review ? (
        <Card>
          <T weight="bold">التقييم</T>
          <Stars value={o.review.rating} />
          {o.review.comment ? <T>{o.review.comment}</T> : null}
        </Card>
      ) : null}
      {kind === 'sales' && o.can_review ? <ReviewForm orderId={o.id} onDone={reload} /> : null}

      <Button title="مشكلة في هذا الطلب؟ أبلغ الإدارة" variant="ghost" icon="chatbubbles-outline"
        onPress={() => navigation.navigate('ContactAdmin', { kind: 'order', order: o.id })} />

      <SectionTitle title="سجل الحالات" />
      <Card>
        {o.status_logs.map((l: any, i: number) => (
          <Row key={i} style={{ alignItems: 'flex-start', paddingVertical: 2 }} gap={space.sm}>
            <Ionicons name="ellipse" size={10} color={colors.gold} style={{ marginTop: 8 }} />
            <View style={{ flex: 1 }}>
              <T size={13} weight="semibold">{LOG_NAMES[l.to_status] ?? l.to_status}</T>
              <T size={12} color={colors.muted}>{l.actor_name ?? ''} · {dateTimeText(l.created_at)}{l.note && l.note !== 'إنشاء الطلب' ? ` · ${l.note}` : ''}</T>
            </View>
          </Row>
        ))}
      </Card>
    </Screen>
  );
}
