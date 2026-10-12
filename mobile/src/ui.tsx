import React, { ReactNode, useState } from 'react';
import {
  ActivityIndicator,
  I18nManager,
  Image,
  Platform,
  Pressable,
  ScrollView,
  StyleProp,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  TextStyle,
  View,
  ViewStyle,
  RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, fonts, radius, shadow, space } from './theme';

/**
 * RTL: on the web the document has dir="rtl"; on phones the app is forced RTL.
 * If a phone still runs LTR (e.g. Expo Go ignoring forcesRTL), flip rows manually.
 */
export const FLIP = Platform.OS !== 'web' && !I18nManager.isRTL;
export const ROW: ViewStyle['flexDirection'] = FLIP ? 'row-reverse' : 'row';
export const TEXT_ALIGN: TextStyle['textAlign'] = FLIP ? 'right' : Platform.OS === 'web' ? 'right' : 'left';
/** Icon that points "forward" in Arabic (towards the left). */
export const FORWARD_ICON = 'chevron-back' as const;

type TextProps = {
  children?: ReactNode;
  style?: StyleProp<TextStyle>;
  weight?: 'regular' | 'semibold' | 'bold';
  size?: number;
  color?: string;
  center?: boolean;
  numberOfLines?: number;
  selectable?: boolean;
};

export function T({ children, style, weight = 'regular', size = 15, color = colors.text, center, numberOfLines, selectable }: TextProps) {
  return (
    <Text
      numberOfLines={numberOfLines}
      selectable={selectable}
      style={[
        { fontFamily: fonts[weight], fontSize: size, color, lineHeight: Math.round(size * 1.6), writingDirection: 'rtl' },
        { textAlign: center ? 'center' : TEXT_ALIGN },
        style,
      ]}
    >
      {children}
    </Text>
  );
}

export function Row({ children, style, gap = space.sm, wrap }: { children: ReactNode; style?: StyleProp<ViewStyle>; gap?: number; wrap?: boolean }) {
  return <View style={[{ flexDirection: ROW, alignItems: 'center', gap, flexWrap: wrap ? 'wrap' : 'nowrap' }, style]}>{children}</View>;
}

export function Screen({
  children, scroll = true, refreshing, onRefresh, padded = true, style,
}: { children: ReactNode; scroll?: boolean; refreshing?: boolean; onRefresh?: () => void; padded?: boolean; style?: StyleProp<ViewStyle> }) {
  const inner = <View style={[{ width: '100%', maxWidth: 980, alignSelf: 'center', padding: padded ? space.lg : 0, gap: space.md }, style]}>{children}</View>;
  if (!scroll) return <View style={{ flex: 1, backgroundColor: colors.bg }}>{inner}</View>;
  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: colors.bg }}
      contentContainerStyle={{ paddingBottom: space.xxl }}
      keyboardShouldPersistTaps="handled"
      refreshControl={onRefresh ? <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor={colors.primary} /> : undefined}
    >
      {inner}
    </ScrollView>
  );
}

export function Card({ children, style, onPress }: { children: ReactNode; style?: StyleProp<ViewStyle>; onPress?: () => void }) {
  const base = [styles.card, style];
  if (onPress) {
    return (
      <Pressable onPress={onPress} style={({ pressed }) => [...base, pressed && { opacity: 0.85 }]} accessibilityRole="button">
        {children}
      </Pressable>
    );
  }
  return <View style={base}>{children}</View>;
}

type BtnProps = {
  title: string;
  onPress?: () => void | Promise<void>;
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost' | 'gold';
  icon?: keyof typeof Ionicons.glyphMap;
  disabled?: boolean;
  loading?: boolean;
  small?: boolean;
  style?: StyleProp<ViewStyle>;
  disabledReason?: string;
};

export function Button({ title, onPress, variant = 'primary', icon, disabled, loading, small, style, disabledReason }: BtnProps) {
  const [busy, setBusy] = useState(false);
  const v = {
    primary: { bg: colors.primary, fg: colors.white, border: colors.primary },
    secondary: { bg: colors.primarySoft, fg: colors.primaryDark, border: colors.primarySoft },
    outline: { bg: 'transparent', fg: colors.primary, border: colors.primary },
    danger: { bg: colors.danger, fg: colors.white, border: colors.danger },
    ghost: { bg: 'transparent', fg: colors.primary, border: 'transparent' },
    gold: { bg: colors.gold, fg: colors.white, border: colors.gold },
  }[variant];
  const isBusy = loading || busy;
  const off = disabled || isBusy;
  const press = async () => {
    if (off || !onPress) return;
    try {
      setBusy(true);
      await onPress();
    } finally {
      setBusy(false);
    }
  };
  return (
    <View style={style}>
      <Pressable
        onPress={press}
        disabled={off}
        accessibilityRole="button"
        accessibilityState={{ disabled: off }}
        style={({ pressed }) => [
          styles.btn,
          small && styles.btnSmall,
          { backgroundColor: v.bg, borderColor: v.border, opacity: off ? 0.5 : pressed ? 0.85 : 1 },
        ]}
      >
        {isBusy ? (
          <ActivityIndicator color={v.fg} size="small" />
        ) : (
          <Row gap={6} style={{ justifyContent: 'center' }}>
            {icon ? <Ionicons name={icon} size={small ? 16 : 18} color={v.fg} /> : null}
            <T weight="semibold" size={small ? 13 : 15} color={v.fg} center>
              {title}
            </T>
          </Row>
        )}
      </Pressable>
      {disabled && disabledReason ? <T size={12} color={colors.muted} center>{disabledReason}</T> : null}
    </View>
  );
}

export function Field({ label, error, hint, ...props }: TextInputProps & { label?: string; error?: string; hint?: string }) {
  return (
    <View style={{ gap: 4 }}>
      {label ? <T weight="semibold" size={14}>{label}</T> : null}
      <TextInput
        placeholderTextColor="#A39E92"
        {...props}
        style={[
          styles.input,
          { textAlign: TEXT_ALIGN, writingDirection: 'rtl' },
          props.multiline && { minHeight: 90, textAlignVertical: 'top', paddingTop: 10 },
          error ? { borderColor: colors.danger } : null,
          props.style,
        ]}
      />
      {hint ? <T size={12} color={colors.muted}>{hint}</T> : null}
      {error ? <T size={12} color={colors.danger}>{error}</T> : null}
    </View>
  );
}

export function Chips<V extends string | number>({
  options, value, onChange, allowNone,
}: { options: { value: V; label: string }[]; value: V | null | undefined; onChange: (v: V | null) => void; allowNone?: boolean }) {
  return (
    <Row wrap gap={6}>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <Pressable
            key={String(o.value)}
            onPress={() => onChange(active && allowNone ? null : o.value)}
            style={[styles.chip, active && { backgroundColor: colors.primary, borderColor: colors.primary }]}
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
          >
            <T size={13} weight="semibold" color={active ? colors.white : colors.text}>{o.label}</T>
          </Pressable>
        );
      })}
    </Row>
  );
}

export function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <Pressable onPress={() => onChange(!value)} accessibilityRole="checkbox" accessibilityState={{ checked: value }}>
      <Row>
        <Ionicons name={value ? 'checkbox' : 'square-outline'} size={22} color={value ? colors.primary : colors.muted} />
        <T>{label}</T>
      </Row>
    </Pressable>
  );
}

export function Badge({ text, tone = 'neutral' }: { text: string; tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'primary' | 'gold' }) {
  const t = {
    neutral: [colors.border, colors.text],
    success: [colors.successSoft, colors.success],
    warning: [colors.warningSoft, colors.warning],
    danger: [colors.dangerSoft, colors.danger],
    primary: [colors.primarySoft, colors.primaryDark],
    gold: [colors.goldSoft, '#7A5A2B'],
  }[tone];
  return (
    <View style={{ backgroundColor: t[0], borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 2, alignSelf: 'flex-start' }}>
      <T size={12} weight="semibold" color={t[1]}>{text}</T>
    </View>
  );
}

export function Loading({ text = 'جارٍ التحميل…' }: { text?: string }) {
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.primary} size="large" />
      <T color={colors.muted} center>{text}</T>
    </View>
  );
}

export function ErrorView({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <View style={[styles.center, styles.stateBox, { borderColor: colors.dangerSoft }]}>
      <Ionicons name="alert-circle-outline" size={36} color={colors.danger} />
      <T center color={colors.danger}>{message}</T>
      {onRetry ? <Button title="إعادة المحاولة" variant="outline" small onPress={onRetry} /> : null}
    </View>
  );
}

export function Empty({ title, subtitle, icon = 'file-tray-outline', action }: { title: string; subtitle?: string; icon?: keyof typeof Ionicons.glyphMap; action?: ReactNode }) {
  return (
    <View style={[styles.center, styles.stateBox]}>
      <Ionicons name={icon} size={40} color={colors.gold} />
      <T weight="semibold" center>{title}</T>
      {subtitle ? <T center color={colors.muted} size={13}>{subtitle}</T> : null}
      {action}
    </View>
  );
}

export function Notice({ text, tone = 'info' }: { text: string; tone?: 'info' | 'success' | 'warning' | 'danger' }) {
  const t = {
    info: [colors.primarySoft, colors.primaryDark, 'information-circle-outline'],
    success: [colors.successSoft, colors.success, 'checkmark-circle-outline'],
    warning: [colors.warningSoft, colors.warning, 'warning-outline'],
    danger: [colors.dangerSoft, colors.danger, 'alert-circle-outline'],
  }[tone] as [string, string, keyof typeof Ionicons.glyphMap];
  return (
    <Row style={{ backgroundColor: t[0], padding: space.md, borderRadius: radius.md, alignItems: 'flex-start' }}>
      <Ionicons name={t[2]} size={20} color={t[1]} />
      <T size={13} color={t[1]} style={{ flex: 1 }}>{text}</T>
    </Row>
  );
}

export function SectionTitle({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <Row style={{ justifyContent: 'space-between', marginTop: space.sm }}>
      <T weight="bold" size={18}>{title}</T>
      {action}
    </Row>
  );
}

export function KV({ k, v }: { k: string; v: ReactNode }) {
  return (
    <Row style={{ justifyContent: 'space-between', paddingVertical: 4 }}>
      <T color={colors.muted} size={14}>{k}</T>
      {typeof v === 'string' || typeof v === 'number' ? <T weight="semibold" size={14} style={{ flexShrink: 1 }}>{v}</T> : v}
    </Row>
  );
}

export function Stars({ value, count, size = 14 }: { value: number | string; count?: number; size?: number }) {
  const n = Number(value) || 0;
  return (
    <Row gap={2}>
      <Ionicons name={count === 0 ? 'star-outline' : 'star'} size={size} color={colors.gold} />
      <T size={size - 1} weight="semibold">{count === 0 ? 'جديد' : n.toFixed(1)}</T>
      {count ? <T size={size - 2} color={colors.muted}>({count})</T> : null}
    </Row>
  );
}

export function Thumb({ uri, size = 72, style }: { uri?: string; size?: number; style?: StyleProp<any> }) {
  return uri ? (
    <Image source={{ uri }} style={[{ width: size, height: size, borderRadius: radius.md, backgroundColor: colors.border }, style]} />
  ) : (
    <View style={[{ width: size, height: size, borderRadius: radius.md, backgroundColor: colors.goldSoft, alignItems: 'center', justifyContent: 'center' }, style]}>
      <Ionicons name="image-outline" size={size / 3} color={colors.gold} />
    </View>
  );
}

export function Divider() {
  return <View style={{ height: 1, backgroundColor: colors.border, marginVertical: space.sm }} />;
}

/** Simple select implemented as a collapsible chip list (works the same on web and phones). */
export function Select<V extends string | number>({
  label, options, value, onChange, placeholder = 'اختر…', allowNone,
}: { label?: string; options: { value: V; label: string }[]; value: V | null | undefined; onChange: (v: V | null) => void; placeholder?: string; allowNone?: boolean }) {
  const [open, setOpen] = useState(false);
  const current = options.find((o) => o.value === value);
  return (
    <View style={{ gap: 4 }}>
      {label ? <T weight="semibold" size={14}>{label}</T> : null}
      <Pressable onPress={() => setOpen(!open)} style={styles.input} accessibilityRole="button">
        <Row style={{ justifyContent: 'space-between', flex: 1 }}>
          <T color={current ? colors.text : '#A39E92'}>{current ? current.label : placeholder}</T>
          <Ionicons name={open ? 'chevron-up' : 'chevron-down'} size={18} color={colors.muted} />
        </Row>
      </Pressable>
      {open ? (
        <View style={{ padding: space.sm, backgroundColor: colors.card, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border }}>
          <Chips
            options={allowNone ? [{ value: '__none__' as any, label: 'الكل' }, ...options] : options}
            value={value ?? ('__none__' as any)}
            onChange={(v) => {
              onChange(v === ('__none__' as any) ? null : v);
              setOpen(false);
            }}
          />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: space.lg, borderWidth: 1, borderColor: colors.border, gap: space.sm, ...shadow },
  btn: { minHeight: 46, borderRadius: radius.md, paddingHorizontal: space.lg, alignItems: 'center', justifyContent: 'center', borderWidth: 1.5 },
  btnSmall: { minHeight: 36, paddingHorizontal: space.md },
  input: {
    minHeight: 46, borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, backgroundColor: colors.white,
    paddingHorizontal: space.md, fontFamily: fonts.regular, fontSize: 15, color: colors.text, justifyContent: 'center',
  },
  chip: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.pill, paddingHorizontal: 12, paddingVertical: 4, backgroundColor: colors.white },
  center: { alignItems: 'center', justifyContent: 'center', gap: space.sm, padding: space.xl },
  stateBox: { backgroundColor: colors.card, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border },
});
