import React, { useState } from 'react';
import { Pressable, View } from 'react-native';
import { colors, money, radius, space } from './theme';
import { Card, Row, T } from './ui';

// Single-series bar color, validated (lightness, chroma, ≥3:1 contrast) against the card surface.
const BAR = '#2F8A57';

/** KPI tile: one headline number. Negative values carry a sign and a word, not only color. */
export function StatTile({ label, value, note, emphasis, count }: { label: string; value: string | number; note?: string; emphasis?: boolean; count?: boolean }) {
  const n = Number(value);
  const negative = !Number.isNaN(n) && n < 0;
  return (
    <Card style={{ flexGrow: 1, flexBasis: 150, padding: space.md, gap: 2, ...(emphasis ? { borderColor: colors.primary, borderWidth: 1.5 } : {}) }}>
      <T size={12} color={colors.muted}>{label}</T>
      <T weight="bold" size={20} color={negative ? colors.danger : colors.text}>{count ? String(value) : money(value)}</T>
      {negative ? <T size={11} color={colors.danger}>خسارة تقديرية</T> : null}
      {note ? <T size={11} color={colors.muted}>{note}</T> : null}
    </Card>
  );
}

/** Horizontal bar list (one series). Each row also shows its value, so it doubles as the table view. */
export function BarList({ rows }: { rows: { label: string; value: number; detail?: string }[] }) {
  const [active, setActive] = useState<number | null>(null);
  const max = Math.max(...rows.map((r) => r.value), 0);
  if (!rows.length) return null;
  return (
    <View style={{ gap: 6 }}>
      {rows.map((r, i) => (
        <Pressable key={r.label} onPress={() => setActive(active === i ? null : i)} accessibilityLabel={`${r.label}: ${money(r.value)}`}
          style={{ paddingVertical: 2 }}>
          <Row gap={space.sm}>
            <T size={12} color={colors.muted} style={{ width: 64 }}>{r.label}</T>
            <View style={{ flex: 1, height: 14, justifyContent: 'center' }}>
              <View style={{ height: 10, width: `${max ? Math.max(2, (r.value / max) * 100) : 0}%`, backgroundColor: BAR, borderTopLeftRadius: radius.sm / 2, borderBottomLeftRadius: radius.sm / 2, opacity: active === null || active === i ? 1 : 0.55 }} />
            </View>
            <T size={12} weight="semibold" style={{ width: 84 }}>{money(r.value)}</T>
          </Row>
          {active === i && r.detail ? <T size={11} color={colors.muted} style={{ marginStart: 72 }}>{r.detail}</T> : null}
        </Pressable>
      ))}
    </View>
  );
}
