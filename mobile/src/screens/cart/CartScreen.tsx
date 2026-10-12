import React, { useState } from 'react';
import { Pressable, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { api, ApiError, imageUrl } from '../../api/client';
import { Address } from '../../api/types';
import { useAuth } from '../../auth';
import { useCart } from '../../cart';
import { QtyStepper } from '../../components';
import { useToast } from '../../feedback';
import { useApi } from '../../hooks';
import { colors, money, qty, space } from '../../theme';
import { Button, Card, Chips, Empty, ErrorView, Field, Notice, Row, Screen, SectionTitle, T, Thumb } from '../../ui';

function Checkout({ kind, pickup, delivery, onPlaced, hasService }: { kind: 'sales' | 'purchase'; pickup: boolean; delivery: boolean; onPlaced: (id: number) => void; hasService?: boolean }) {
  const { me } = useAuth();
  const toast = useToast();
  const addresses = useApi<Address[]>(me ? '/addresses/' : null);
  const [fulfillment, setFulfillment] = useState<'pickup' | 'delivery'>(pickup ? 'pickup' : 'delivery');
  const [addressId, setAddressId] = useState<number | null>(null);
  const [notes, setNotes] = useState('');
  const [date, setDate] = useState('');
  const [error, setError] = useState<string | null>(null);
  const cart = useCart();

  const place = async () => {
    setError(null);
    if (fulfillment === 'delivery' && !addressId) return setError('اختر عنوان التوصيل أو أضف عنوانًا جديدًا.');
    if (date && !/^\d{4}-\d{2}-\d{2}$/.test(date)) return setError('اكتب التاريخ بالشكل 2026-10-20');
    try {
      const body: any = { fulfillment, address_id: fulfillment === 'delivery' ? addressId : null, notes };
      let order: any;
      if (kind === 'sales') {
        body.items = cart.sales.map((l) => ({ offer_id: l.offer.id, quantity: l.quantity }));
        if (date) body.requested_date = date;
        order = await api('/sales-orders/', { method: 'POST', body });
        cart.clearSales();
      } else {
        body.items = cart.materials.map((l) => ({ material_id: l.material.id, quantity: String(l.quantity) }));
        order = await api('/purchase-orders/', { method: 'POST', body });
        cart.clearMaterials();
      }
      toast(`تم إنشاء الطلب #${order.id} وهو بانتظار القبول.`);
      onPlaced(order.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر إنشاء الطلب');
    }
  };

  const options = [pickup && { value: 'pickup', label: 'استلام' }, delivery && { value: 'delivery', label: 'توصيل' }].filter(Boolean) as any[];
  return (
    <Card>
      <T weight="bold">طريقة الاستلام</T>
      <Chips options={options} value={fulfillment} onChange={(v) => v && setFulfillment(v as any)} />
      {fulfillment === 'delivery' ? (
        <View style={{ gap: space.sm }}>
          <T weight="semibold" size={14}>عنوان التوصيل (يظهر للبائع فقط لتنفيذ الطلب)</T>
          {addresses.data?.length ? (
            <>
              <Chips options={addresses.data.map((a) => ({ value: a.id, label: `${a.map_url ? '📍 ' : ''}${a.label}: ${a.city_name}` }))} value={addressId} onChange={setAddressId} />
              {addressId ? (
                <T size={12} color={colors.muted}>{addresses.data.find((a) => a.id === addressId)?.full_text}</T>
              ) : null}
            </>
          ) : (
            <T size={13} color={colors.muted}>لا توجد عناوين محفوظة.</T>
          )}
          <AddAddressLink />
          <Notice text="يحدد البائع تكلفة التوصيل بعد قبول الطلب، ويوضح من يدفعها وهل هي نهائية أو تقديرية." />
        </View>
      ) : null}
      {hasService ? <Field label="الموعد المفضل للخدمة (اختياري)" value={date} onChangeText={setDate} placeholder="2026-10-20" /> : null}
      <Field label="ملاحظات للبائع (اختياري)" value={notes} onChangeText={setNotes} multiline />
      {error ? <ErrorView message={error} /> : null}
      <Button title="تأكيد الطلب" icon="checkmark-circle-outline" onPress={place} />
      <T size={12} color={colors.muted}>لا يوجد دفع إلكتروني. يتم الاتفاق على الدفع مباشرة مع البائع عند الاستلام.</T>
    </Card>
  );
}

function AddAddressLink() {
  const nav = useNavigation<any>();
  return <Button small variant="ghost" icon="add" title="إضافة / إدارة العناوين" onPress={() => nav.navigate('Addresses')} />;
}

export default function CartScreen({ navigation }: any) {
  const cart = useCart();
  const { me } = useAuth();
  const [tab, setTab] = useState<'sales' | 'materials'>(cart.sales.length || !cart.materials.length ? 'sales' : 'materials');

  const salesTotal = cart.sales.reduce((s, l) => s + Number(l.offer.price) * l.quantity, 0);
  const matTotal = cart.materials.reduce((s, l) => s + Number(l.material.price) * l.quantity, 0);
  const biz = cart.sales[0]?.offer.business;
  const sup = cart.materials[0]?.material.supplier;

  return (
    <Screen>
      <Chips options={[{ value: 'sales', label: `المنتجات والخدمات (${cart.sales.length})` }, { value: 'materials', label: `المواد الخام (${cart.materials.length})` }]}
        value={tab} onChange={(v) => v && setTab(v as any)} />
      {tab === 'sales' ? (
        !cart.sales.length ? (
          <Empty icon="bag-outline" title="سلتك فارغة" subtitle="تصفح العروض وأضف ما يعجبك." action={<Button small title="تصفح العروض" onPress={() => navigation.navigate('Search', {})} />} />
        ) : (
          <>
            <Notice text={`الطلب من مشروع واحد: ${biz?.name}`} />
            {cart.sales.map((l) => (
              <Card key={l.offer.id}>
                <Row style={{ alignItems: 'flex-start' }}>
                  <Thumb uri={imageUrl(l.offer.images[0]?.image)} size={64} />
                  <View style={{ flex: 1 }}>
                    <T weight="semibold">{l.offer.title}</T>
                    <T size={13} color={colors.muted}>{money(l.offer.price)} {l.offer.price_unit}</T>
                    <Row style={{ justifyContent: 'space-between' }}>
                      <QtyStepper value={l.quantity} onChange={(v) => cart.setOfferQty(l.offer.id, v)} max={l.offer.available_quantity ?? 99} />
                      <Pressable onPress={() => cart.removeOffer(l.offer.id)} accessibilityLabel="حذف"><Ionicons name="trash-outline" size={20} color={colors.danger} /></Pressable>
                    </Row>
                  </View>
                </Row>
              </Card>
            ))}
            <Row style={{ justifyContent: 'space-between' }}><T weight="bold">المجموع التقديري</T><T weight="bold" color={colors.primary}>{money(salesTotal)}</T></Row>
            {me ? (
              <Checkout kind="sales" pickup={biz!.pickup_available} delivery={biz!.delivery_available}
                hasService={cart.sales.some((l) => l.offer.offer_type === 'service')}
                onPlaced={(id) => navigation.navigate('Order', { kind: 'sales', id })} />
            ) : (
              <Button title="سجّل الدخول لإتمام الطلب" onPress={() => navigation.navigate('Login')} />
            )}
          </>
        )
      ) : !cart.materials.length ? (
        <Empty icon="layers-outline" title="سلة المواد فارغة" subtitle="سلة المواد الخام لأصحاب المشاريع لشراء المستلزمات من الموردين." action={<Button small title="تصفح المواد" onPress={() => navigation.navigate('Materials')} />} />
      ) : (
        <>
          <Notice text={`طلب شراء من مورد واحد: ${sup?.name}`} />
          {cart.materials.map((l) => (
            <Card key={l.material.id}>
              <Row style={{ alignItems: 'flex-start' }}>
                <Thumb uri={imageUrl(l.material.images[0]?.image)} size={64} />
                <View style={{ flex: 1 }}>
                  <T weight="semibold">{l.material.title}</T>
                  <T size={13} color={colors.muted}>{money(l.material.price)} لكل {l.material.unit_display} · الحد الأدنى {qty(l.material.min_order_quantity)}</T>
                  <Row style={{ justifyContent: 'space-between' }}>
                    <QtyStepper value={l.quantity} onChange={(v) => cart.setMaterialQty(l.material.id, v)} min={Number(l.material.min_order_quantity)} max={Number(l.material.available_quantity)} step={['piece', 'pack', 'box'].includes(l.material.unit) ? 1 : 0.5} />
                    <Pressable onPress={() => cart.removeMaterial(l.material.id)}><Ionicons name="trash-outline" size={20} color={colors.danger} /></Pressable>
                  </Row>
                </View>
              </Row>
            </Card>
          ))}
          <Row style={{ justifyContent: 'space-between' }}><T weight="bold">المجموع التقديري</T><T weight="bold" color={colors.primary}>{money(matTotal)}</T></Row>
          {me?.business_profile_id ? (
            <Checkout kind="purchase" pickup={sup!.pickup_available} delivery={sup!.delivery_available}
              onPlaced={(id) => navigation.navigate('Order', { kind: 'purchase', id })} />
          ) : (
            <Notice tone="warning" text="شراء المواد متاح لأصحاب المشاريع. أنشئ ملف مشروعك من «حسابي» أولًا." />
          )}
        </>
      )}
    </Screen>
  );
}
