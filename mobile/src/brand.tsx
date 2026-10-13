import React from 'react';
import { Image, View } from 'react-native';
import { colors } from './theme';
import { Row, T } from './ui';

/** Site identity: logo + «مهنتي» + tagline. `light` for dark backgrounds. */
export function Brand({ light = false, size = 'md' }: { light?: boolean; size?: 'md' | 'lg' }) {
  const logo = size === 'lg' ? 56 : 44;
  return (
    <Row gap={10}>
      <Image
        source={require('../assets/icon.png')}
        accessibilityLabel="شعار مهنتي"
        style={{ width: logo, height: logo, borderRadius: logo / 2, borderWidth: 2, borderColor: colors.gold }}
      />
      <View>
        <T weight="bold" size={size === 'lg' ? 26 : 22} color={light ? '#fff' : colors.primaryDark} style={{ lineHeight: size === 'lg' ? 36 : 30 }}>
          مهنتي
        </T>
        <T size={12} color={light ? colors.goldSoft : colors.muted} style={{ lineHeight: 18 }}>
          منصة تمكين المشاريع المنزلية
        </T>
      </View>
    </Row>
  );
}
