import React, { useState } from 'react';
import { Image, ImageBackground, Pressable, ScrollView, TextInput, useWindowDimensions, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../auth';
import { OfferCard } from '../../components';
import { useApi } from '../../hooks';
import { imageUrl } from '../../api/client';
import { BusinessCard, Offer, Paged } from '../../api/types';
import { CATEGORY_ICONS, useRefData } from '../../refdata';
import { colors, fonts, radius, shadow, space } from '../../theme';
import { Card, Empty, ErrorView, Loading, Row, SectionTitle, Stars, T, TEXT_ALIGN, Thumb } from '../../ui';

export default function HomeScreen({ navigation }: any) {
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const wide = width >= 760;
  const { me } = useAuth();
  const [q, setQ] = useState('');
  const { offerCategories } = useRefData();
  const offers = useApi<Paged<Offer>>('/offers/', { ordering: 'newest', available: 1 });
  const businesses = useApi<Paged<BusinessCard & { category: any }>>('/businesses/');
  const unread = useApi<{ count: number }>(me ? '/notifications/unread_count/' : null);

  const submit = () => navigation.navigate('Search', { q });

  return (
    <ScrollView style={{ flex: 1, backgroundColor: colors.bg }} contentContainerStyle={{ paddingBottom: space.xxl }}>
      <ImageBackground source={require('../../../assets/background.jpg')} resizeMode="cover" style={{ paddingTop: insets.top + space.md, overflow: 'hidden', backgroundColor: colors.primaryDark }} imageStyle={{ width: '100%', height: '100%' }}>
        <View style={{ backgroundColor: 'rgba(20,63,43,0.55)', padding: space.lg, paddingBottom: space.xl }}>
          <View style={{ width: '100%', maxWidth: 980, alignSelf: 'center', gap: space.md }}>
            <Row style={{ justifyContent: 'space-between' }}>
              <Row>
                <Image source={require('../../../assets/icon.png')} style={{ width: 44, height: 44, borderRadius: 22, borderWidth: 2, borderColor: colors.gold }} />
                <View>
                  <T weight="bold" size={22} color="#fff">مهنتي</T>
                  <T size={12} color={colors.goldSoft}>منصة تمكين المشاريع المنزلية</T>
                </View>
              </Row>
              {me ? (
                <Pressable onPress={() => navigation.navigate('Notifications')} accessibilityLabel="الإشعارات" hitSlop={10}>
                  <Ionicons name="notifications-outline" size={26} color="#fff" />
                  {unread.data?.count ? (
                    <View style={{ position: 'absolute', top: -4, right: -6, backgroundColor: colors.gold, borderRadius: 9, minWidth: 18, height: 18, justifyContent: 'center' }}>
                      <T size={10} color="#fff" center weight="bold">{unread.data.count}</T>
                    </View>
                  ) : null}
                </Pressable>
              ) : (
                <Pressable onPress={() => navigation.navigate('Login')} style={{ borderWidth: 1, borderColor: '#fff', borderRadius: radius.pill, paddingHorizontal: 14, paddingVertical: 4 }}>
                  <T color="#fff" weight="semibold" size={13}>تسجيل الدخول</T>
                </Pressable>
              )}
            </Row>
            <T weight="bold" size={wide ? 30 : 24} color="#fff" style={{ marginTop: space.md }}>
              {me ? `أهلًا ${me.full_name.split(' ')[0]}،` : 'أهلًا بك،'} ماذا تبحث اليوم؟
            </T>
            <T color="#F3E9D8" size={14}>منتجات وخدمات منزلية من أصحاب مشاريع قريبين منك، ومواد خام من موردين موثوقين.</T>
            <Row style={{ backgroundColor: '#fff', borderRadius: radius.md, paddingHorizontal: space.md, ...shadow }}>
              <Ionicons name="search" size={20} color={colors.muted} />
              <TextInput
                value={q}
                onChangeText={setQ}
                onSubmitEditing={submit}
                returnKeyType="search"
                placeholder="ابحث: تطريز، معمول، هدية…"
                placeholderTextColor="#A39E92"
                style={{ flex: 1, height: 48, fontFamily: fonts.regular, fontSize: 15, textAlign: TEXT_ALIGN, color: colors.text }}
              />
              <Pressable onPress={submit} accessibilityLabel="بحث"><Ionicons name="arrow-back-circle" size={30} color={colors.primary} /></Pressable>
            </Row>
            <Pressable onPress={() => navigation.navigate('SmartSearch', { target: 'offers' })}
              style={{ backgroundColor: colors.gold, borderRadius: radius.md, padding: space.md, ...shadow }}>
              <Row>
                <Ionicons name="sparkles" size={22} color="#fff" />
                <View style={{ flex: 1 }}>
                  <T weight="bold" color="#fff">المساعد الذكي</T>
                  <T size={12} color="#fff">اكتب طلبك بكلماتك: «هدية مطرزة بأقل من 100 شيكل من نابلس»</T>
                </View>
                <Ionicons name="chevron-back" size={20} color="#fff" />
              </Row>
            </Pressable>
          </View>
        </View>
      </ImageBackground>

      <View style={{ width: '100%', maxWidth: 980, alignSelf: 'center', padding: space.lg, gap: space.md }}>
        <SectionTitle title="التصنيفات" action={<Pressable onPress={() => navigation.navigate('Categories')}><T color={colors.primary} weight="semibold" size={13}>عرض الكل</T></Pressable>} />
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.sm }}>
          {offerCategories.map((c) => (
            <Pressable key={c.id} onPress={() => navigation.navigate('Search', { category: c.id, q: '' })}
              style={{ backgroundColor: colors.card, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, padding: space.md, alignItems: 'center', width: 96, gap: 4 }}>
              <View style={{ backgroundColor: colors.primarySoft, borderRadius: 24, width: 48, height: 48, alignItems: 'center', justifyContent: 'center' }}>
                <Ionicons name={(CATEGORY_ICONS[c.name] ?? 'pricetag-outline') as any} size={24} color={colors.primary} />
              </View>
              <T size={12} weight="semibold" center numberOfLines={1}>{c.name}</T>
            </Pressable>
          ))}
        </ScrollView>

        <Card onPress={() => navigation.navigate('Materials')} style={{ backgroundColor: colors.primary, borderColor: colors.primary }}>
          <Row>
            <Ionicons name="layers" size={28} color={colors.goldSoft} />
            <View style={{ flex: 1 }}>
              <T weight="bold" color="#fff">قسم الموردين والمواد الخام</T>
              <T size={13} color={colors.goldSoft}>قارن أسعار الأقمشة والخيوط والمستلزمات حسب الوحدة والحد الأدنى والتوصيل.</T>
            </View>
            <Ionicons name="chevron-back" size={20} color="#fff" />
          </Row>
        </Card>

        <SectionTitle title="أحدث العروض المتاحة" action={<Pressable onPress={() => navigation.navigate('Search', {})}><T color={colors.primary} weight="semibold" size={13}>عرض الكل</T></Pressable>} />
        {offers.loading ? <Loading /> : offers.error ? <ErrorView message={offers.error} onRetry={offers.reload} /> :
          !offers.data?.results.length ? <Empty title="لا توجد عروض بعد" subtitle="عندما يضيف أصحاب المشاريع منتجاتهم ستظهر هنا." /> : (
            <View style={{ flexDirection: wide ? 'row' : 'column', flexWrap: 'wrap', gap: space.md }}>
              {offers.data.results.slice(0, 6).map((o) => (
                <View key={o.id} style={{ width: wide ? '48.5%' : '100%' }}><OfferCard offer={o} /></View>
              ))}
            </View>
          )}

        <SectionTitle title="مشاريع منزلية مميزة" />
        {businesses.loading ? <Loading /> : businesses.error ? <ErrorView message={businesses.error} onRetry={businesses.reload} /> : (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.md }}>
            {businesses.data?.results.map((b) => (
              <Card key={b.id} onPress={() => navigation.navigate('Business', { id: b.id })} style={{ width: 200, alignItems: 'center' }}>
                <Thumb uri={imageUrl(b.logo)} size={56} />
                <T weight="bold" center numberOfLines={1}>{b.name}</T>
                <T size={12} color={colors.muted} center>{b.category?.name} · {b.city_name}</T>
                <Stars value={b.rating_avg} count={b.rating_count} />
              </Card>
            ))}
          </ScrollView>
        )}

        <Card onPress={() => navigation.navigate('ContactAdmin')} style={{ marginTop: space.md, backgroundColor: colors.goldSoft, borderColor: colors.gold }}>
          <Row>
            <Ionicons name="chatbubbles-outline" size={26} color="#7A5A2B" />
            <View style={{ flex: 1 }}>
              <T weight="bold">واجهت مشكلة أو محتوى مخالفًا؟</T>
              <T size={13} color={colors.muted}>تواصل مع الإدارة للإبلاغ، ويصل بلاغك إلى واتساب الإدارة.</T>
            </View>
            <Ionicons name="chevron-back" size={20} color="#7A5A2B" />
          </Row>
        </Card>
      </View>
    </ScrollView>
  );
}
