import React, { useState } from 'react';
import { Linking, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api, ApiError } from '../../api/client';
import { StatusBadge } from '../../components';
import { useToast } from '../../feedback';
import { useApi } from '../../hooks';
import { colors, dateText, dateTimeText, money, space } from '../../theme';
import { Button, Card, Chips, ErrorView, Field, KV, Loading, Notice, Row, Screen, SectionTitle, T } from '../../ui';

const UPDATABLE = [
  { value: 'created', label: 'مسجلة' },
  { value: 'picked_up', label: 'استلمتها الشركة' },
  { value: 'in_transit', label: 'في الطريق' },
  { value: 'delivered', label: 'تم التسليم' },
  { value: 'failed', label: 'تعذر التسليم' },
  { value: 'returned', label: 'مرتجعة' },
];

export default function ShipmentScreen({ route, navigation }: any) {
  const { data: s, error, loading, reload, setData } = useApi<any>(`/shipments/${route.params.id}/`);
  const toast = useToast();
  const [status, setStatus] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const [tracking, setTracking] = useState<string | null>(null);

  if (loading && !s) return <Screen><Loading /></Screen>;
  if (error || !s) return <Screen><ErrorView message={error ?? ''} onRetry={reload} /></Screen>;

  const update = async () => {
    try {
      setData(await api(`/shipments/${s.id}/update_status/`, { method: 'POST', body: { status: status ?? s.status, note, ...(tracking !== null ? { tracking_number: tracking } : {}) } }));
      setNote('');
      toast('تم تحديث الشحنة.');
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر التحديث', 'error');
    }
  };
  const retry = async () => {
    try {
      setData(await api(`/shipments/${s.id}/retry/`, { method: 'POST' }));
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر الاتصال', 'error');
    }
  };
  const closed = ['delivered', 'returned'].includes(s.status);

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <Card>
        <Row style={{ justifyContent: 'space-between' }}>
          <T weight="bold" size={18}>شحنة #{s.id}</T>
          <StatusBadge status={s.status} label={s.status_display} />
        </Row>
        <T size={13} color={colors.muted}>{s.kind_display}</T>
        <KV k="الطلب" v={`#${s.order_id}`} />
        <KV k="شركة التوصيل" v={s.carrier_display || '—'} />
        <KV k="رقم التتبع" v={s.tracking_number || 'غير متوفر'} />
        <KV k="التكلفة" v={s.cost ? `${money(s.cost)} (${s.cost_is_final ? 'نهائية' : 'تقديرية'})` : 'غير محددة'} />
        <KV k="الوصول المتوقع" v={s.estimated_arrival ? dateText(s.estimated_arrival) : 'غير محدد'} />
        <KV k="آخر تحديث" v={dateTimeText(s.last_update)} />
        <KV k="المرسل / المستلم" v={`${s.sender_name} ← ${s.recipient_name}`} />
        {s.external_confirmed ? <Notice tone="success" text="مؤكدة من نظام شركة التوصيل." /> : <Notice text="بيانات مسجلة يدويًا من المرسل (غير مرتبطة آليًا بنظام شركة التوصيل)." />}
        {s.last_error ? <Notice tone="warning" text={`لم تؤكد شركة التوصيل الشحنة بعد: ${s.last_error}`} /> : null}
        <Button small variant="ghost" title="فتح الطلب" onPress={() => navigation.navigate('Order', { kind: s.kind, id: s.order_id })} />
      </Card>
      <Card>
        <T weight="bold">عنوان التسليم</T>
        <T>{s.delivery_address.recipient_name} · {s.delivery_address.phone}</T>
        <T color={colors.muted}>{s.delivery_address.city}{s.delivery_address.area ? ` - ${s.delivery_address.area}` : ''} · {s.delivery_address.address}</T>
        {s.delivery_address.map_url ? (
          <Button small variant="outline" icon="map-outline" title="فتح موقع التسليم على الخريطة" onPress={() => Linking.openURL(s.delivery_address.map_url)} />
        ) : null}
      </Card>
      {s.my_role === 'sender' && s.status === 'pending_carrier' ? <Button title="إعادة محاولة الاتصال بشركة التوصيل" variant="outline" onPress={retry} /> : null}
      {s.my_role === 'sender' && !closed ? (
        <Card>
          <T weight="bold">تحديث الحالة</T>
          <Chips options={UPDATABLE} value={status ?? s.status} onChange={setStatus} />
          <Field label="رقم التتبع" value={tracking ?? s.tracking_number} onChangeText={setTracking} />
          <Field value={note} onChangeText={setNote} placeholder="ملاحظة (اختياري)" />
          <Button title="حفظ التحديث" onPress={update} />
        </Card>
      ) : null}
      <SectionTitle title="سجل التتبع" />
      <Card>
        {s.events.map((e: any, i: number) => (
          <Row key={i} style={{ alignItems: 'flex-start' }} gap={space.sm}>
            <Ionicons name="ellipse" size={10} color={colors.gold} style={{ marginTop: 8 }} />
            <View style={{ flex: 1 }}>
              <T size={13} weight="semibold">{e.status_display}</T>
              <T size={12} color={colors.muted}>{dateTimeText(e.created_at)}{e.note ? ` · ${e.note}` : ''}</T>
            </View>
          </Row>
        ))}
      </Card>
    </Screen>
  );
}
