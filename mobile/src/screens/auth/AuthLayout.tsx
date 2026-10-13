import React, { ReactNode, useState } from 'react';
import {
  Image, KeyboardAvoidingView, Platform, Pressable, ScrollView, TextInput, TextInputProps,
  useWindowDimensions, View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { colors, fonts, radius, shadow, space } from '../../theme';
import { Row, T, TEXT_ALIGN } from '../../ui';

const BENEFITS: { icon: keyof typeof Ionicons.glyphMap; text: string }[] = [
  { icon: 'gift-outline', text: 'اطلب منتجات وخدمات منزلية من مشاريع قريبة منك' },
  { icon: 'storefront-outline', text: 'اعرض منتجات مشروعك وتابع طلباتك ومبيعاتك' },
  { icon: 'layers-outline', text: 'اشترِ المواد الخام وقارن أسعار الموردين' },
];

// Wall green sampled from the artwork's edges, so the panel blends with the picture.
const ART_GREEN = '#20432D';
const ART_RATIO = 1407 / 926;

/**
 * Shared look for sign-in / sign-up. The artwork (which already carries the name «مهنتي» and the
 * tagline) is shown uncovered.
 * Wide screens: artwork + benefits in a green panel beside the form. Phones: artwork on top, form below.
 */
export function AuthLayout({ title, subtitle, onBack, children }: { title: string; subtitle: string; onBack: () => void; children: ReactNode }) {
  const { width, height } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const wide = width >= 860;

  const back = (
    <Pressable onPress={onBack} accessibilityRole="button" accessibilityLabel="رجوع" hitSlop={12}
      style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(20,40,28,0.55)', alignItems: 'center', justifyContent: 'center' }}>
      <Ionicons name="chevron-forward" size={22} color="#fff" />
    </Pressable>
  );

  // Explicit size (react-native-web ignores aspectRatio on images and falls back to the natural height).
  const artW = wide ? Math.min(640, (width * 1.1) / 2.1 - space.xxl * 2) : width;
  const art = (style: object) => (
    <Image source={require('../../../assets/login-art.jpg')} accessibilityLabel="مهنتي - منصة تمكين المشاريع المنزلية"
      resizeMode="cover" style={[{ width: artW, height: artW / ART_RATIO, alignSelf: 'center' }, style]} />
  );

  const card = (
    <View style={{ backgroundColor: colors.card, borderRadius: radius.lg + 4, padding: space.xl, gap: space.md, borderWidth: 1, borderColor: colors.border, ...shadow }}>
      <View style={{ gap: 2 }}>
        <T weight="bold" size={24}>{title}</T>
        <T color={colors.muted} size={14}>{subtitle}</T>
      </View>
      {children}
    </View>
  );

  if (wide) {
    return (
      <View style={{ flex: 1, flexDirection: 'row', backgroundColor: colors.bg }}>
        <ScrollView style={{ flex: 1.1, backgroundColor: ART_GREEN }}
          contentContainerStyle={{ flexGrow: 1, padding: space.xxl, paddingTop: insets.top + space.xl, gap: space.xl, justifyContent: 'center' }}>
          <Row>{back}</Row>
          <View style={{ width: '100%', maxWidth: 640, alignSelf: 'center', gap: space.xl }}>
            {art({ borderRadius: radius.lg + 4, borderWidth: 1, borderColor: 'rgba(184,146,90,0.45)' })}
            <View style={{ gap: space.md }}>
              <T weight="bold" size={28} color="#fff" style={{ lineHeight: 44 }}>كل ما يحتاجه مشروعك المنزلي في مكان واحد</T>
              {BENEFITS.map((b) => (
                <Row key={b.text} gap={space.md}>
                  <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: 'rgba(243,233,216,0.14)', alignItems: 'center', justifyContent: 'center' }}>
                    <Ionicons name={b.icon} size={18} color={colors.goldSoft} />
                  </View>
                  <T color="#F3E9D8" size={15} style={{ flex: 1 }}>{b.text}</T>
                </Row>
              ))}
            </View>
          </View>
        </ScrollView>
        <ScrollView style={{ flex: 1 }} contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', padding: space.xxl, minHeight: height }} keyboardShouldPersistTaps="handled">
          <View style={{ width: '100%', maxWidth: 440, alignSelf: 'center' }}>{card}</View>
        </ScrollView>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.bg }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ paddingBottom: space.xxl }} keyboardShouldPersistTaps="handled">
        <View style={{ backgroundColor: ART_GREEN, paddingTop: insets.top }}>
          {art({})}
          <View style={{ position: 'absolute', top: insets.top + space.md, left: space.md, right: space.md }}>
            <Row>{back}</Row>
          </View>
        </View>
        <View style={{ paddingHorizontal: space.lg, marginTop: space.lg, width: '100%', maxWidth: 480, alignSelf: 'center' }}>{card}</View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

/** Text input with a leading icon; `secure` adds a show/hide toggle. */
export function IconField({ label, icon, secure, error, ...props }: TextInputProps & { label: string; icon: keyof typeof Ionicons.glyphMap; secure?: boolean; error?: boolean }) {
  const [hidden, setHidden] = useState(true);
  const [focused, setFocused] = useState(false);
  return (
    <View style={{ gap: 6 }}>
      <T weight="semibold" size={14}>{label}</T>
      <Row gap={space.sm} style={{
        minHeight: 50, borderRadius: radius.md, borderWidth: 1.5, paddingHorizontal: space.md, backgroundColor: colors.white,
        borderColor: error ? colors.danger : focused ? colors.primary : colors.border,
      }}>
        <Ionicons name={icon} size={20} color={focused ? colors.primary : colors.muted} />
        <TextInput
          placeholderTextColor="#A39E92"
          {...props}
          secureTextEntry={secure ? hidden : props.secureTextEntry}
          onFocus={(e) => { setFocused(true); props.onFocus?.(e); }}
          onBlur={(e) => { setFocused(false); props.onBlur?.(e); }}
          style={[{ flex: 1, minWidth: 0, height: 48, fontFamily: fonts.regular, fontSize: 15, color: colors.text, textAlign: TEXT_ALIGN, writingDirection: 'rtl' },
            Platform.OS === 'web' ? ({ outlineStyle: 'none' } as any) : null]}
        />
        {secure ? (
          <Pressable onPress={() => setHidden(!hidden)} hitSlop={10} accessibilityRole="button" accessibilityLabel={hidden ? 'إظهار كلمة المرور' : 'إخفاء كلمة المرور'}>
            <Ionicons name={hidden ? 'eye-outline' : 'eye-off-outline'} size={20} color={colors.muted} />
          </Pressable>
        ) : null}
      </Row>
    </View>
  );
}

export function FormError({ message }: { message: string }) {
  return (
    <Row style={{ backgroundColor: colors.dangerSoft, borderRadius: radius.md, padding: space.md, alignItems: 'flex-start' }} gap={space.sm}>
      <Ionicons name="alert-circle" size={18} color={colors.danger} />
      <T size={13} color={colors.danger} style={{ flex: 1 }}>{message}</T>
    </Row>
  );
}

/** Footer line like «ليس لديك حساب؟ أنشئ حسابًا». */
export function SwitchLink({ question, action, onPress }: { question: string; action: string; onPress: () => void }) {
  return (
    <Row gap={6} style={{ justifyContent: 'center', paddingTop: space.sm, borderTopWidth: 1, borderTopColor: colors.border, marginTop: space.xs }}>
      <T color={colors.muted} size={14}>{question}</T>
      <Pressable onPress={onPress} accessibilityRole="link" hitSlop={8}>
        <T weight="bold" color={colors.primary} size={14}>{action}</T>
      </Pressable>
    </Row>
  );
}
