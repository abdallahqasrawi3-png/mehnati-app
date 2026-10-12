import React from 'react';
import { View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { CATEGORY_ICONS, useRefData } from '../../refdata';
import { colors, space } from '../../theme';
import { Card, ErrorView, Loading, Row, Screen, SectionTitle, T } from '../../ui';

export default function CategoriesScreen({ navigation }: any) {
  const { offerCategories, materialCategories, loaded, error } = useRefData();
  if (error) return <Screen><ErrorView message={error} /></Screen>;
  if (!loaded) return <Screen><Loading /></Screen>;
  const grid = (list: typeof offerCategories, onPress: (id: number) => void) => (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.md }}>
      {list.map((c) => (
        <Card key={c.id} onPress={() => onPress(c.id)} style={{ width: 150, alignItems: 'center' }}>
          <Ionicons name={(CATEGORY_ICONS[c.name] ?? 'pricetag-outline') as any} size={28} color={colors.primary} />
          <T weight="semibold" center>{c.name}</T>
        </Card>
      ))}
    </View>
  );
  return (
    <Screen>
      <SectionTitle title="منتجات وخدمات منزلية" />
      {grid(offerCategories, (id) => navigation.navigate('Main', { screen: 'Search', params: { category: id, q: '' } }))}
      <SectionTitle title="المواد الخام" />
      {grid(materialCategories, (id) => navigation.navigate('Main', { screen: 'Materials', params: { category: id } }))}
      <Row><T size={12} color={colors.muted}>تدير إدارة المنصة التصنيفات وتضيف الجديد منها.</T></Row>
    </Screen>
  );
}
