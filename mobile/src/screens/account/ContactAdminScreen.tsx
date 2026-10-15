import React, { useState } from 'react';
import { Linking, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api, ApiError } from '../../api/client';
import { useAuth } from '../../auth';
import { colors, radius, space } from '../../theme';
import { Button, Card, Chips, ErrorView, Field, Notice, Row, Screen, T } from '../../ui';

const KINDS = [
  { value: 'problem', label: 'مشكلة في التطبيق' },
  { value: 'abuse', label: 'بلاغ عن محتوى أو مستخدم' },
  { value: 'order', label: 'شكوى على طلب' },
  { value: 'suggestion', label: 'اقتراح' },
  { value: 'other', label: 'أخرى' },
];

/** Report to the platform administrator: saved on the server, then sent to the admin's WhatsApp. */
export default function ContactAdminScreen({ route, navigation }: any) {
  const { me } = useAuth();
  const [form, setForm] = useState({
    kind: route.params?.kind ?? 'problem',
    name: me?.full_name.replace('[تجريبي]', '').trim() ?? '',
    phone: me?.phone ?? '',
    order_ref: route.params?.order ? String(route.params.order) : '',
    message: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<{ id: number; whatsapp_url: string } | null>(null);
  const set = (k: keyof typeof form) => (v: string | null) => setForm((f) => ({ ...f, [k]: v ?? '' }));

  const openWhatsApp = (url: string) => Linking.openURL(url).catch(() => setError('تعذر فتح واتساب. انسخ الرقم وراسل الإدارة مباشرة.'));

  const send = async () => {
    setError(null);
    if (form.name.trim().length < 2) return setError('اكتب اسمك.');
    if (form.message.trim().length < 10) return setError('اكتب تفاصيل البلاغ (10 أحرف على الأقل).');
    try {
      const r = await api<{ id: number; whatsapp_url: string }>('/contact-admin/', { method: 'POST', body: form });
      setSent(r);
      openWhatsApp(r.whatsapp_url);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر إرسال البلاغ');
    }
  };

  if (sent) {
    return (
      <Screen style={{ maxWidth: 560 }}>
        <Card style={{ alignItems: 'center', gap: space.md }}>
          <View style={{ width: 64, height: 64, borderRadius: 32, backgroundColor: colors.successSoft, alignItems: 'center', justifyContent: 'center' }}>
            <Ionicons name="checkmark-circle" size={40} color={colors.success} />
          </View>
          <T weight="bold" size={20} center>تم حفظ بلاغك رقم #{sent.id}</T>
          <T center color={colors.muted}>فُتح واتساب برسالة جاهزة فيها تفاصيل البلاغ. اضغط «إرسال» في واتساب لتصل الرسالة إلى الإدارة مباشرة.</T>
          <Button title="فتح واتساب وإرسال البلاغ" icon="logo-whatsapp" onPress={() => openWhatsApp(sent.whatsapp_url)} style={{ alignSelf: 'stretch' }} />
          <Button title="رجوع" variant="ghost" onPress={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('Main'))} />
        </Card>
      </Screen>
    );
  }

  return (
    <Screen style={{ maxWidth: 640 }}>
      <Row style={{ backgroundColor: colors.primarySoft, borderRadius: radius.lg, padding: space.lg, alignItems: 'flex-start' }} gap={space.md}>
        <Ionicons name="shield-checkmark-outline" size={28} color={colors.primary} />
        <View style={{ flex: 1, gap: 4 }}>
          <T weight="bold" size={17}>تواصل مع الإدارة للإبلاغ</T>
          <T size={13} color={colors.muted}>
            أبلغ عن مشكلة أو محتوى مخالف أو شكوى على طلب. يُحفظ البلاغ لدى الإدارة، ثم يُفتح واتساب برسالة جاهزة إلى رقم الإدارة.
          </T>
        </View>
      </Row>
      <Card>
        <T weight="semibold" size={14}>نوع البلاغ</T>
        <Chips options={KINDS} value={form.kind} onChange={(v) => v && set('kind')(v)} />
        <Field label="اسمك *" value={form.name} onChangeText={set('name')} />
        <Field label="رقم هاتفك (اختياري، للتواصل معك)" value={form.phone} onChangeText={set('phone')} keyboardType="phone-pad" />
        {form.kind === 'order' ? (
          <Field label="رقم الطلب" value={form.order_ref} onChangeText={set('order_ref')} keyboardType="numeric" placeholder="مثال: 15" />
        ) : null}
        <Field label="تفاصيل البلاغ *" value={form.message} onChangeText={set('message')} multiline
          placeholder="اشرح ما حدث: اسم المحل أو المنتج، ومتى، وما المشكلة." />
        {error ? <ErrorView message={error} /> : null}
        <Button title="إرسال البلاغ عبر واتساب" icon="logo-whatsapp" onPress={send} />
        <Notice text="لن يُرسل شيء تلقائيًا: يفتح واتساب برسالة جاهزة وأنت من يضغط «إرسال»." />
      </Card>
    </Screen>
  );
}
