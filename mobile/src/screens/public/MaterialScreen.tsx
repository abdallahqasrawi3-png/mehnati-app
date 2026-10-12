import React, { useEffect, useState } from 'react';
import { Material } from '../../api/types';
import { useAuth } from '../../auth';
import { useCart } from '../../cart';
import { Gallery, QtyStepper } from '../../components';
import { useToast } from '../../feedback';
import { useApi } from '../../hooks';
import ReportAbuse from '../../ReportAbuse';
import { colors, money, qty } from '../../theme';
import { Badge, Button, Card, ErrorView, KV, Loading, Notice, Row, Screen, T } from '../../ui';

export default function MaterialScreen({ route, navigation }: any) {
  const { data: m, error, loading, reload } = useApi<Material>(`/materials/${route.params.id}/`);
  const { me } = useAuth();
  const cart = useCart();
  const toast = useToast();
  const [q, setQ] = useState(1);
  useEffect(() => {
    if (m) setQ(Number(m.min_order_quantity));
  }, [m?.id]);

  if (loading && !m) return <Screen><Loading /></Screen>;
  if (error || !m) return <Screen><ErrorView message={error ?? ''} onRetry={reload} /></Screen>;
  const avail = Number(m.available_quantity);
  const minQ = Number(m.min_order_quantity);
  const own = me?.supplier_profile_id === m.supplier.id;
  const canBuy = !!me?.business_profile_id && !own && m.is_available && avail >= minQ;

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <Gallery images={m.images} />
      <Row wrap gap={6}><Badge text={m.category.name} tone="primary" /><Badge text={`الوحدة: ${m.unit_display}`} tone="gold" /></Row>
      <T weight="bold" size={22}>{m.title}</T>
      <T weight="bold" size={22} color={colors.primary}>{money(m.price)} <T size={14} color={colors.muted}>لكل {m.unit_display}</T></T>
      <Card>
        <KV k="المتاح" v={`${qty(avail)} ${m.unit_display}`} />
        <KV k="الحد الأدنى للشراء" v={`${qty(minQ)} ${m.unit_display}`} />
        <KV k="مدة التجهيز" v={`${m.preparation_days} يوم`} />
        <KV k="الاستلام" v={m.supplier.pickup_available ? 'متاح' : 'غير متاح'} />
        <KV k="التوصيل" v={m.supplier.delivery_available ? `${m.supplier.delivery_days ?? '؟'} يوم · ${m.supplier.delivery_cost ? money(m.supplier.delivery_cost) + ' تقديرية' : 'التكلفة يحددها المورد'}` : 'غير متاح'} />
      </Card>
      {m.specifications ? <Card><T weight="semibold">المواصفات</T><T>{m.specifications}</T></Card> : null}
      {m.description ? <Card><T weight="semibold">الوصف</T><T>{m.description}</T></Card> : null}
      <Card onPress={() => navigation.navigate('Supplier', { id: m.supplier.id })}>
        <T size={13} color={colors.muted}>المورد</T>
        <T weight="bold">{m.supplier.name}</T>
        <T size={13} color={colors.muted}>{m.supplier.city_name}</T>
      </Card>
      {canBuy ? (
        <Card>
          <Row style={{ justifyContent: 'space-between' }}>
            <T weight="semibold">الكمية ({m.unit_display})</T>
            <QtyStepper value={q} onChange={setQ} min={minQ} max={avail} step={m.unit === 'piece' || m.unit === 'pack' || m.unit === 'box' ? 1 : 0.5} />
          </Row>
          <T size={13} color={colors.muted}>المجموع التقديري: {money(Number(m.price) * q)}</T>
          <Button title="أضف إلى سلة المواد" icon="bag-add-outline" onPress={() => {
            const { replaced } = cart.addMaterial(m, q);
            toast(replaced ? 'أُفرغت سلة المواد السابقة (طلب الشراء من مورد واحد).' : 'أضيفت إلى سلة المواد.', replaced ? 'info' : 'success');
          }} />
        </Card>
      ) : !me ? (
        <Button title="سجّل الدخول لطلب المواد" variant="outline" onPress={() => navigation.navigate('Login')} />
      ) : own ? (
        <Notice text="هذه مادة من حسابك كمورد." />
      ) : !me.business_profile_id ? (
        <Notice tone="warning" text="شراء المواد الخام متاح لأصحاب المشاريع المنزلية. أنشئ ملف مشروعك من «حسابي»." />
      ) : (
        <Notice tone="warning" text="الكمية المتاحة أقل من الحد الأدنى أو المادة غير متاحة حاليًا." />
      )}
      <ReportAbuse type="material" id={m.id} />
    </Screen>
  );
}
