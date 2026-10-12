import React from 'react';
import { Image, Pressable, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../auth';
import { confirm } from '../../feedback';
import { useApi } from '../../hooks';
import { colors, radius, space } from '../../theme';
import { Badge, Button, Card, FORWARD_ICON, Notice, Row, Screen, SectionTitle, T } from '../../ui';

function Item({ icon, title, subtitle, onPress, badge }: { icon: any; title: string; subtitle?: string; onPress: () => void; badge?: string | number }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={({ pressed }) => [{ paddingVertical: space.sm, opacity: pressed ? 0.6 : 1 }]}>
      <Row>
        <View style={{ width: 38, height: 38, borderRadius: 19, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' }}>
          <Ionicons name={icon} size={20} color={colors.primary} />
        </View>
        <View style={{ flex: 1 }}>
          <T weight="semibold">{title}</T>
          {subtitle ? <T size={12} color={colors.muted}>{subtitle}</T> : null}
        </View>
        {badge ? <Badge text={String(badge)} tone="gold" /> : null}
        <Ionicons name={FORWARD_ICON} size={18} color={colors.muted} />
      </Row>
    </Pressable>
  );
}

export default function AccountScreen({ navigation }: any) {
  const { me, logout, ready } = useAuth();
  const unread = useApi<{ count: number }>(me ? '/notifications/unread_count/' : null);
  const low = useApi<{ offers: any[]; materials: any[] }>(me && (me.business_profile_id || me.supplier_profile_id) ? '/inventory/low-stock/' : null);
  const go = (name: string, params?: any) => () => navigation.navigate(name, params);

  if (!ready) return <Screen><T>…</T></Screen>;
  if (!me) {
    return (
      <Screen style={{ maxWidth: 520 }}>
        <Image source={require('../../../assets/wordmark.jpg')} style={{ width: '100%', height: 120, borderRadius: radius.lg }} resizeMode="contain" />
        <Card>
          <T weight="bold" size={18} center>مرحبًا بك في مهنتي</T>
          <T center color={colors.muted}>سجّل الدخول لتتابع طلباتك، أو لتعرض منتجات مشروعك المنزلي، أو لتبيع المواد الخام كمورد.</T>
          <Button title="تسجيل الدخول" onPress={go('Login')} />
          <Button title="إنشاء حساب جديد" variant="outline" onPress={go('Register')} />
        </Card>
      </Screen>
    );
  }
  const lowCount = (low.data?.offers.length ?? 0) + (low.data?.materials.length ?? 0);

  return (
    <Screen refreshing={false} onRefresh={() => { unread.reload(); low.reload(); }}>
      <Card style={{ backgroundColor: colors.primary, borderColor: colors.primary }}>
        <T weight="bold" size={20} color="#fff">{me.full_name}</T>
        <T color={colors.goldSoft} size={13}>{me.email}</T>
        <Row wrap gap={6}>
          <Badge text="عميل" tone="gold" />
          {me.business_profile_id ? <Badge text="صاحب مشروع" tone="gold" /> : null}
          {me.supplier_profile_id ? <Badge text="مورد" tone="gold" /> : null}
          {me.is_staff ? <Badge text="مدير المنصة" tone="gold" /> : null}
        </Row>
      </Card>

      {lowCount ? <Notice tone="warning" text={`لديك ${lowCount} عنصرًا وصل مخزونه إلى حد التنبيه.`} /> : null}

      <SectionTitle title="كعميل" />
      <Card>
        <Item icon="receipt-outline" title="طلباتي" subtitle="تتبع طلباتك وألغِ أو قيّم" onPress={go('Orders', { kind: 'sales', role: 'customer' })} />
        <Item icon="notifications-outline" title="الإشعارات" onPress={go('Notifications')} badge={unread.data?.count || undefined} />
        <Item icon="car-outline" title="الشحنات" subtitle="شحنات طلباتك المرسلة والواردة" onPress={go('Shipments')} />
        <Item icon="location-outline" title="عناويني" subtitle="خاصة، تظهر للبائع عند الطلب فقط" onPress={go('Addresses')} />
        <Item icon="person-outline" title="بياناتي وكلمة المرور" onPress={go('Profile')} />
      </Card>

      <SectionTitle title="مشروعي المنزلي" />
      <Card>
        {me.business_profile_id ? (
          <>
            <Item icon="storefront-outline" title="ملف المشروع وصور الأعمال" onPress={go('BusinessEdit')} />
            <Item icon="pricetags-outline" title="منتجاتي وخدماتي والمخزون" onPress={go('MyOffers')} badge={low.data?.offers.length || undefined} />
            <Item icon="file-tray-full-outline" title="طلبات العملاء" onPress={go('Orders', { kind: 'sales', role: 'business' })} />
            <Item icon="cart-outline" title="طلبات شراء المواد الخام" subtitle="مشترياتك من الموردين" onPress={go('Orders', { kind: 'purchase', role: 'buyer' })} />
            <Item icon="stats-chart-outline" title="التقارير المالية والمصاريف" onPress={go('BusinessReports')} />
            <Item icon="eye-outline" title="عرض صفحتي العامة" onPress={go('Business', { id: me.business_profile_id })} />
          </>
        ) : (
          <>
            <T color={colors.muted}>اعرض منتجاتك وخدماتك المنزلية واستقبل الطلبات وتابع مبيعاتك وتكاليفك.</T>
            <Button title="أنشئ ملف مشروعك المنزلي" icon="add-circle-outline" onPress={go('BusinessEdit')} />
          </>
        )}
      </Card>

      <SectionTitle title="المورد" />
      <Card>
        {me.supplier_profile_id ? (
          <>
            <Item icon="business-outline" title="ملف المورد" onPress={go('SupplierEdit')} />
            <Item icon="layers-outline" title="موادي الخام والمخزون" onPress={go('MyMaterials')} badge={low.data?.materials.length || undefined} />
            <Item icon="file-tray-full-outline" title="طلبات الشراء الواردة" onPress={go('Orders', { kind: 'purchase', role: 'supplier' })} />
            <Item icon="stats-chart-outline" title="تقارير المورد" onPress={go('SupplierReports')} />
          </>
        ) : (
          <>
            <T color={colors.muted}>تبيع أقمشة أو خيوط أو أدوات أو مكونات؟ اعرضها لأصحاب المشاريع.</T>
            <Button title="سجّل كمورد" variant="outline" icon="add-circle-outline" onPress={go('SupplierEdit')} />
          </>
        )}
      </Card>

      {me.is_staff ? (
        <>
          <SectionTitle title="الإدارة" />
          <Card><Item icon="shield-checkmark-outline" title="لوحة مدير المنصة" subtitle="المؤشرات والبلاغات والحسابات" onPress={go('Admin')} /></Card>
        </>
      ) : null}

      <Button title="تسجيل الخروج" variant="danger" icon="log-out-outline" onPress={async () => { if (await confirm('تسجيل الخروج؟')) await logout(); }} />
    </Screen>
  );
}
