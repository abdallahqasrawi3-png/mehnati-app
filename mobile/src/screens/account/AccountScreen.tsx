import React from 'react';
import { Image, ImageBackground, Pressable, RefreshControl, ScrollView, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Paged } from '../../api/types';
import { useAuth } from '../../auth';
import { Brand } from '../../brand';
import { confirm } from '../../feedback';
import { useApi } from '../../hooks';
import { colors, radius, shadow, space } from '../../theme';
import { Badge, Button, Loading, Notice, Row, T } from '../../ui';

const OPEN_SALES = 'pending,accepted,preparing,ready,in_transit,delivery_failed';
const OPEN_PURCHASE = 'pending,accepted,preparing,shipped';
const DEMO_TAG = '[تجريبي]';

type TileProps = { icon: keyof typeof Ionicons.glyphMap; title: string; onPress: () => void; badge?: number; tone?: 'primary' | 'gold' };

/** Square shortcut: icon, label and an optional count badge. */
function Tile({ icon, title, onPress, badge, tone = 'primary', width }: TileProps & { width: number }) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={badge ? `${title} (${badge})` : title}
      style={({ pressed }) => [{
        width, minHeight: 104, backgroundColor: colors.card, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border,
        alignItems: 'center', justifyContent: 'center', padding: space.sm, gap: 6, opacity: pressed ? 0.75 : 1, ...shadow,
      }]}
    >
      <View style={{ width: 46, height: 46, borderRadius: 23, alignItems: 'center', justifyContent: 'center', backgroundColor: tone === 'gold' ? colors.goldSoft : colors.primarySoft }}>
        <Ionicons name={icon} size={23} color={tone === 'gold' ? '#7A5A2B' : colors.primary} />
      </View>
      <T size={13} weight="semibold" center numberOfLines={2}>{title}</T>
      {badge ? (
        <View style={{ position: 'absolute', top: 8, left: 8, minWidth: 22, height: 22, borderRadius: 11, paddingHorizontal: 6, backgroundColor: colors.gold, alignItems: 'center', justifyContent: 'center' }}>
          <T size={11} weight="bold" color="#fff" center style={{ lineHeight: 16 }}>{badge > 99 ? '99+' : badge}</T>
        </View>
      ) : null}
    </Pressable>
  );
}

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <View style={{ gap: space.sm }}>
      <View>
        <T weight="bold" size={17}>{title}</T>
        {subtitle ? <T size={12} color={colors.muted}>{subtitle}</T> : null}
      </View>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>{children}</View>
    </View>
  );
}

function Stat({ label, value, icon, onPress, warn }: { label: string; value: number | undefined; icon: keyof typeof Ionicons.glyphMap; onPress: () => void; warn?: boolean }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={({ pressed }) => [{ flex: 1, minWidth: 76, alignItems: 'center', paddingVertical: space.sm, gap: 2, opacity: pressed ? 0.7 : 1 }]}>
      <Ionicons name={icon} size={18} color={warn && value ? colors.warning : colors.primary} />
      <T weight="bold" size={20} center color={warn && value ? colors.warning : colors.text}>{value ?? '–'}</T>
      <T size={11} color={colors.muted} center>{label}</T>
    </Pressable>
  );
}

function CreateCard({ icon, title, text, action, onPress }: { icon: keyof typeof Ionicons.glyphMap; title: string; text: string; action: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={({ pressed }) => [{
      width: '100%', borderRadius: radius.lg, borderWidth: 1.5, borderStyle: 'dashed', borderColor: colors.gold,
      backgroundColor: colors.goldSoft, padding: space.lg, gap: space.sm, opacity: pressed ? 0.8 : 1,
    }]}>
      <Row>
        <Ionicons name={icon} size={26} color="#7A5A2B" />
        <T weight="bold" style={{ flex: 1 }}>{title}</T>
      </Row>
      <T size={13} color={colors.muted}>{text}</T>
      <Row gap={4}>
        <Ionicons name="add-circle" size={18} color={colors.primary} />
        <T weight="semibold" color={colors.primary}>{action}</T>
      </Row>
    </Pressable>
  );
}

export default function AccountScreen({ navigation }: any) {
  const { me, logout, ready } = useAuth();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const contentW = Math.min(width, 980) - space.lg * 2;
  // 6 on wide screens fits the business section (6 tiles) in one row; 3 on phones.
  const cols = contentW >= 740 ? 6 : contentW >= 500 ? 4 : 3;
  const tileW = Math.floor((contentW - space.sm * (cols - 1)) / cols);

  const hasBiz = !!me?.business_profile_id;
  const hasSup = !!me?.supplier_profile_id;
  const unread = useApi<{ count: number }>(me ? '/notifications/unread_count/' : null);
  const myOpen = useApi<Paged<unknown>>(me ? '/sales-orders/' : null, { role: 'customer', status: OPEN_SALES });
  const bizOpen = useApi<Paged<unknown>>(hasBiz ? '/sales-orders/' : null, { role: 'business', status: OPEN_SALES });
  const supOpen = useApi<Paged<unknown>>(hasSup ? '/purchase-orders/' : null, { role: 'supplier', status: OPEN_PURCHASE });
  const low = useApi<{ offers: unknown[]; materials: unknown[] }>(hasBiz || hasSup ? '/inventory/low-stock/' : null);
  const go = (name: string, params?: object) => () => navigation.navigate(name, params);
  const tile = (p: TileProps) => <Tile key={p.title} width={tileW} {...p} />;

  const hero = (children: React.ReactNode) => (
    <ImageBackground source={require('../../../assets/background.jpg')} resizeMode="cover" imageStyle={{ width: '100%', height: '100%' }}
      style={{ overflow: 'hidden', backgroundColor: colors.primaryDark }}>
      <View style={{ backgroundColor: 'rgba(20,63,43,0.72)', paddingTop: insets.top + space.lg, paddingBottom: 56, paddingHorizontal: space.lg }}>
        <View style={{ width: '100%', maxWidth: 980, alignSelf: 'center', gap: space.lg }}>{children}</View>
      </View>
    </ImageBackground>
  );

  if (!ready) return <View style={{ flex: 1, backgroundColor: colors.bg }}><Loading /></View>;

  if (!me) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg }}>
        {hero(
          <>
            <Brand light size="lg" />
            <T weight="bold" size={24} color="#fff">أهلًا بك في مهنتي</T>
            <T color={colors.goldSoft}>سجّل الدخول لتتابع طلباتك، أو لتعرض منتجات مشروعك المنزلي، أو لتبيع المواد الخام كمورد.</T>
          </>,
        )}
        <View style={{ width: '100%', maxWidth: 520, alignSelf: 'center', paddingHorizontal: space.lg, marginTop: -36, gap: space.md }}>
          <View style={{ backgroundColor: colors.card, borderRadius: radius.lg, padding: space.lg, gap: space.md, borderWidth: 1, borderColor: colors.border, ...shadow }}>
            <Button title="تسجيل الدخول" icon="log-in-outline" onPress={go('Login')} />
            <Button title="إنشاء حساب جديد" variant="outline" icon="person-add-outline" onPress={go('Register')} />
          </View>
        </View>
      </View>
    );
  }

  const isDemo = me.full_name.includes(DEMO_TAG);
  const name = me.full_name.replace(DEMO_TAG, '').trim() || me.email;
  const initial = name.trim().charAt(0);
  const lowCount = (low.data?.offers.length ?? 0) + (low.data?.materials.length ?? 0);
  const refresh = () => [unread, myOpen, bizOpen, supOpen, low].forEach((x) => x.reload());

  return (
    <View style={{ flex: 1, backgroundColor: colors.bg }}>
        <ScrollArea onRefresh={refresh}>
          {hero(
            <>
              <Row style={{ justifyContent: 'space-between' }}>
                <Brand light />
                <Pressable onPress={go('Notifications')} accessibilityLabel="الإشعارات" hitSlop={10}>
                  <Ionicons name="notifications-outline" size={26} color="#fff" />
                  {unread.data?.count ? (
                    <View style={{ position: 'absolute', top: -4, right: -6, backgroundColor: colors.gold, borderRadius: 9, minWidth: 18, height: 18, justifyContent: 'center' }}>
                      <T size={10} color="#fff" center weight="bold" style={{ lineHeight: 14 }}>{unread.data.count}</T>
                    </View>
                  ) : null}
                </Pressable>
              </Row>
              <Row gap={space.md}>
                <View style={{ width: 72, height: 72, borderRadius: 36, backgroundColor: colors.goldSoft, borderWidth: 3, borderColor: colors.gold, alignItems: 'center', justifyContent: 'center' }}>
                  <T weight="bold" size={30} color={colors.primaryDark} center style={{ lineHeight: 40 }}>{initial}</T>
                </View>
                <View style={{ flex: 1, gap: 2 }}>
                  <T weight="bold" size={22} color="#fff" numberOfLines={1}>{name}</T>
                  <T size={13} color={colors.goldSoft} numberOfLines={1}>{me.email}</T>
                  <Row wrap gap={6} style={{ marginTop: 4 }}>
                    <Badge text="عميل" tone="gold" />
                    {hasBiz ? <Badge text="صاحب مشروع" tone="gold" /> : null}
                    {hasSup ? <Badge text="مورد" tone="gold" /> : null}
                    {me.is_staff ? <Badge text="مدير المنصة" tone="gold" /> : null}
                    {isDemo ? <Badge text="حساب تجريبي" tone="warning" /> : null}
                  </Row>
                </View>
              </Row>
            </>,
          )}

          <View style={{ width: '100%', maxWidth: 980, alignSelf: 'center', paddingHorizontal: space.lg, gap: space.xl, marginTop: -40 }}>
            <View style={{ backgroundColor: colors.card, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, flexDirection: 'row', flexWrap: 'wrap', ...shadow }}>
              <Stat label="طلباتي الجارية" icon="receipt-outline" value={myOpen.data?.count} onPress={go('Orders', { kind: 'sales', role: 'customer' })} />
              <Stat label="إشعارات جديدة" icon="notifications-outline" value={unread.data?.count} onPress={go('Notifications')} />
              {hasBiz ? <Stat label="طلبات العملاء" icon="file-tray-full-outline" value={bizOpen.data?.count} onPress={go('Orders', { kind: 'sales', role: 'business' })} /> : null}
              {hasSup ? <Stat label="طلبات واردة" icon="layers-outline" value={supOpen.data?.count} onPress={go('Orders', { kind: 'purchase', role: 'supplier' })} /> : null}
              {hasBiz || hasSup ? <Stat label="مخزون منخفض" icon="warning-outline" value={lowCount} warn onPress={go(hasBiz ? 'MyOffers' : 'MyMaterials')} /> : null}
            </View>

            {lowCount ? <Notice tone="warning" text={`لديك ${lowCount} عنصرًا وصل مخزونه إلى حد التنبيه.`} /> : null}

            <Section title="حسابي كعميل">
              {tile({ icon: 'receipt-outline', title: 'طلباتي', onPress: go('Orders', { kind: 'sales', role: 'customer' }), badge: myOpen.data?.count })}
              {tile({ icon: 'notifications-outline', title: 'الإشعارات', onPress: go('Notifications'), badge: unread.data?.count })}
              {tile({ icon: 'car-outline', title: 'الشحنات', onPress: go('Shipments') })}
              {tile({ icon: 'location-outline', title: 'عناويني', onPress: go('Addresses') })}
              {tile({ icon: 'person-outline', title: 'بياناتي وكلمة المرور', onPress: go('Profile') })}
            </Section>

            <Section title="مشروعي المنزلي" subtitle={hasBiz ? 'منتجاتك وطلبات عملائك ومبيعاتك' : undefined}>
              {hasBiz ? (
                <>
                  {tile({ icon: 'storefront-outline', title: 'ملف المشروع', onPress: go('BusinessEdit') })}
                  {tile({ icon: 'pricetags-outline', title: 'منتجاتي والمخزون', onPress: go('MyOffers'), badge: low.data?.offers.length })}
                  {tile({ icon: 'file-tray-full-outline', title: 'طلبات العملاء', onPress: go('Orders', { kind: 'sales', role: 'business' }), badge: bizOpen.data?.count })}
                  {tile({ icon: 'cart-outline', title: 'مشتريات المواد', onPress: go('Orders', { kind: 'purchase', role: 'buyer' }) })}
                  {tile({ icon: 'stats-chart-outline', title: 'التقارير المالية', onPress: go('BusinessReports'), tone: 'gold' })}
                  {tile({ icon: 'eye-outline', title: 'صفحتي العامة', onPress: go('Business', { id: me.business_profile_id }) })}
                </>
              ) : (
                <CreateCard icon="storefront-outline" title="ابدأ مشروعك المنزلي على مهنتي" action="أنشئ ملف مشروعك"
                  text="اعرض منتجاتك وخدماتك، واستقبل الطلبات، وتابع مبيعاتك وتكاليفك." onPress={go('BusinessEdit')} />
              )}
            </Section>

            <Section title="المورد" subtitle={hasSup ? 'موادك الخام وطلبات الشراء' : undefined}>
              {hasSup ? (
                <>
                  {tile({ icon: 'business-outline', title: 'ملف المورد', onPress: go('SupplierEdit') })}
                  {tile({ icon: 'layers-outline', title: 'موادي والمخزون', onPress: go('MyMaterials'), badge: low.data?.materials.length })}
                  {tile({ icon: 'file-tray-full-outline', title: 'طلبات الشراء الواردة', onPress: go('Orders', { kind: 'purchase', role: 'supplier' }), badge: supOpen.data?.count })}
                  {tile({ icon: 'stats-chart-outline', title: 'تقارير المورد', onPress: go('SupplierReports'), tone: 'gold' })}
                </>
              ) : (
                <CreateCard icon="business-outline" title="تبيع مواد خام أو مستلزمات؟" action="سجّل كمورد"
                  text="أقمشة، خيوط، أدوات، مكونات… اعرضها لأصحاب المشاريع المنزلية." onPress={go('SupplierEdit')} />
              )}
            </Section>

            {me.is_staff ? (
              <Section title="الإدارة">
                {tile({ icon: 'shield-checkmark-outline', title: 'لوحة مدير المنصة', onPress: go('Admin'), tone: 'gold' })}
              </Section>
            ) : null}

            <View style={{ gap: space.md, alignItems: 'center', paddingTop: space.sm }}>
              <Button title="تسجيل الخروج" variant="outline" icon="log-out-outline" style={{ width: '100%', maxWidth: 360 }}
                onPress={async () => { if (await confirm('تسجيل الخروج؟')) await logout(); }} />
              <Row gap={6}>
                <Image source={require('../../../assets/icon.png')} style={{ width: 20, height: 20, borderRadius: 10 }} />
                <T size={12} color={colors.muted}>مهنتي · منصة تمكين المشاريع المنزلية</T>
              </Row>
            </View>
          </View>
        </ScrollArea>
    </View>
  );
}

/** Full-bleed scroll view (the hero spans the whole width) with pull-to-refresh. */
function ScrollArea({ children, onRefresh }: { children: React.ReactNode; onRefresh: () => void }) {
  const [refreshing, setRefreshing] = React.useState(false);
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.bg }}
      contentContainerStyle={{ paddingBottom: space.xxl }}
      refreshControl={<RefreshControl refreshing={refreshing} tintColor={colors.primary} onRefresh={() => { setRefreshing(true); onRefresh(); setTimeout(() => setRefreshing(false), 600); }} />}
    >
      {children}
    </ScrollView>
  );
}
