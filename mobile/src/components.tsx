import React, { useState } from 'react';
import { Image, Platform, Pressable, ScrollView, useWindowDimensions, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';
import { imageUrl, uploadImage, ApiError } from './api/client';
import { Img, Material, Offer } from './api/types';
import { colors, money, qty, radius, space } from './theme';
import { Badge, Button, Card, Row, Stars, T, Thumb } from './ui';
import { useToast } from './feedback';

export function offerTypeTone(t: string) {
  return t === 'ready' ? 'success' : t === 'service' ? 'gold' : 'primary';
}

export function prepText(days: number) {
  if (days === 0) return 'جاهز فورًا';
  if (days === 1) return 'خلال يوم';
  if (days === 2) return 'خلال يومين';
  return `خلال ${days} أيام`;
}

export function OfferCard({ offer, compact, onToggleCompare, inCompare }: { offer: Offer; compact?: boolean; onToggleCompare?: () => void; inCompare?: boolean }) {
  const nav = useNavigation<any>();
  return (
    <Card onPress={() => nav.navigate('Offer', { id: offer.id })} style={{ padding: space.md }}>
      <Row style={{ alignItems: 'flex-start' }} gap={space.md}>
        <Thumb uri={imageUrl(offer.images[0]?.image)} size={compact ? 72 : 92} />
        <View style={{ flex: 1, gap: 2 }}>
          <T weight="bold" numberOfLines={2}>{offer.title}</T>
          <Row wrap gap={6}>
            <Badge text={offer.offer_type_display} tone={offerTypeTone(offer.offer_type) as any} />
            {!offer.is_orderable ? <Badge text="غير متاح حاليًا" tone="danger" /> : null}
          </Row>
          <T size={13} color={colors.muted} numberOfLines={1}>
            {offer.business.name} · {offer.business.city_name}
          </T>
          <Row style={{ justifyContent: 'space-between' }}>
            <T weight="bold" color={colors.primary}>
              {money(offer.price)} <T size={12} color={colors.muted}>{offer.price_unit}</T>
            </T>
            <Stars value={offer.business.rating_avg} count={offer.business.rating_count} />
          </Row>
          <Row style={{ justifyContent: 'space-between' }}>
            <T size={12} color={colors.muted}>
              <Ionicons name="time-outline" size={12} /> {prepText(offer.preparation_days)}
              {offer.available_quantity !== null ? ` · المتاح ${offer.available_quantity}` : ''}
            </T>
            {onToggleCompare ? (
              <Pressable onPress={onToggleCompare} hitSlop={8} accessibilityRole="checkbox" accessibilityState={{ checked: !!inCompare }}>
                <Row gap={4}>
                  <Ionicons name={inCompare ? 'checkbox' : 'square-outline'} size={18} color={colors.primary} />
                  <T size={12} color={colors.primary}>مقارنة</T>
                </Row>
              </Pressable>
            ) : null}
          </Row>
        </View>
      </Row>
    </Card>
  );
}

export function MaterialCard({ m, onToggleCompare, inCompare }: { m: Material; onToggleCompare?: () => void; inCompare?: boolean }) {
  const nav = useNavigation<any>();
  return (
    <Card onPress={() => nav.navigate('Material', { id: m.id })} style={{ padding: space.md }}>
      <Row style={{ alignItems: 'flex-start' }} gap={space.md}>
        <Thumb uri={imageUrl(m.images[0]?.image)} size={84} />
        <View style={{ flex: 1, gap: 2 }}>
          <T weight="bold" numberOfLines={2}>{m.title}</T>
          <T size={13} color={colors.muted} numberOfLines={1}>{m.supplier.name} · {m.supplier.city_name}</T>
          <T weight="bold" color={colors.primary}>
            {money(m.price)} <T size={12} color={colors.muted}>لكل {m.unit_display}</T>
          </T>
          <T size={12} color={colors.muted}>
            المتاح {qty(m.available_quantity)} {m.unit_display} · الحد الأدنى {qty(m.min_order_quantity)}
          </T>
          <Row style={{ justifyContent: 'space-between' }}>
            <T size={12} color={colors.muted}>
              {m.supplier.delivery_available
                ? `توصيل ${m.supplier.delivery_days ? `خلال ${m.supplier.delivery_days} يوم` : ''} ${m.supplier.delivery_cost ? `(تقديري ${money(m.supplier.delivery_cost)})` : ''}`
                : 'استلام من المورد فقط'}
            </T>
            {onToggleCompare ? (
              <Pressable onPress={onToggleCompare} hitSlop={8}>
                <Row gap={4}>
                  <Ionicons name={inCompare ? 'checkbox' : 'square-outline'} size={18} color={colors.primary} />
                  <T size={12} color={colors.primary}>مقارنة</T>
                </Row>
              </Pressable>
            ) : null}
          </Row>
        </View>
      </Row>
    </Card>
  );
}

const STATUS_TONES: Record<string, any> = {
  pending: 'warning', accepted: 'primary', preparing: 'primary', ready: 'gold', in_transit: 'gold', shipped: 'gold',
  completed: 'success', received: 'success', delivered: 'success', rejected: 'danger', cancelled: 'danger',
  delivery_failed: 'danger', failed: 'danger', returned: 'danger', created: 'primary', pending_carrier: 'warning', picked_up: 'gold',
};

export function StatusBadge({ status, label }: { status: string; label: string }) {
  return <Badge text={label} tone={STATUS_TONES[status] ?? 'neutral'} />;
}

export function Gallery({ images }: { images: Img[] }) {
  const { width } = useWindowDimensions();
  const w = Math.min(width, 980) - space.lg * 2;
  const [i, setI] = useState(0);
  if (!images.length) return <Thumb size={Math.min(w, 320)} style={{ alignSelf: 'center' }} />;
  return (
    <View style={{ gap: space.sm }}>
      <Image source={{ uri: imageUrl(images[i].image) }} style={{ width: '100%', height: Math.min(w * 0.75, 420), borderRadius: radius.lg, backgroundColor: colors.border }} resizeMode="cover" />
      {images.length > 1 ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: space.sm }}>
          {images.map((img, idx) => (
            <Pressable key={img.id} onPress={() => setI(idx)}>
              <Thumb uri={imageUrl(img.image)} size={60} style={idx === i ? { borderWidth: 2, borderColor: colors.primary } : null} />
            </Pressable>
          ))}
        </ScrollView>
      ) : null}
    </View>
  );
}

/** Pick an image and upload it to the given endpoint. Server validates type and size. */
export function ImageUploadButton({ path, onDone, title = 'إضافة صورة' }: { path: string; onDone: () => void; title?: string }) {
  const toast = useToast();
  const pick = async () => {
    if (Platform.OS !== 'web') {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        toast('يجب السماح بالوصول إلى الصور.', 'error');
        return;
      }
    }
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.8, allowsEditing: false });
    if (res.canceled || !res.assets?.length) return;
    try {
      await uploadImage(path, res.assets[0].uri);
      toast('تم رفع الصورة.');
      onDone();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر رفع الصورة.', 'error');
    }
  };
  return <Button title={title} icon="image-outline" variant="outline" small onPress={pick} />;
}

export function QtyStepper({ value, onChange, min = 1, max, step = 1 }: { value: number; onChange: (v: number) => void; min?: number; max?: number; step?: number }) {
  const dec = () => onChange(Math.max(min, +(value - step).toFixed(2)));
  const inc = () => onChange(max !== undefined ? Math.min(max, +(value + step).toFixed(2)) : +(value + step).toFixed(2));
  return (
    <Row gap={space.sm}>
      <Pressable onPress={dec} style={stepBtn} accessibilityLabel="إنقاص"><Ionicons name="remove" size={18} color={colors.primary} /></Pressable>
      <T weight="bold" style={{ minWidth: 34 }} center>{qty(value)}</T>
      <Pressable onPress={inc} style={stepBtn} accessibilityLabel="زيادة"><Ionicons name="add" size={18} color={colors.primary} /></Pressable>
    </Row>
  );
}

const stepBtn = { width: 34, height: 34, borderRadius: 17, borderWidth: 1, borderColor: colors.primary, alignItems: 'center' as const, justifyContent: 'center' as const };
