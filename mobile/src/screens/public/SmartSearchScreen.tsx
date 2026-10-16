import React, { useState } from 'react';
import { View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api, ApiError } from '../../api/client';
import { MaterialCard, OfferCard } from '../../components';
import { useApi } from '../../hooks';
import { colors, space } from '../../theme';
import { Badge, Button, Card, Chips, Empty, ErrorView, Field, Loading, Notice, Row, Screen, T } from '../../ui';

const EXAMPLES = {
  offers: [
    'أريد هدية مطرزة بأقل من 100 شيكل وتكون جاهزة خلال أربعة أيام ويفضل أن تكون من جنين',
    'معمول منزلي من رام الله خلال يومين',
    'خدمة تعليم تطريز بتقييم عالي',
  ],
  materials: [
    'أريد قماشًا مناسبًا للتطريز بسعر جيد ويصل إلى منطقتي خلال يومين',
    'خيوط تطريز قطنية أقل من 30 شيكل',
  ],
};

type Result = { item: any; match: 'full' | 'near'; reasons: string[]; unmet: string[] };
type Resp = { source: 'ai' | 'rules'; criteria: { mandatory: string[]; preferences: string[] }; message: string; results: Result[] };

export default function SmartSearchScreen({ route }: any) {
  const [target, setTarget] = useState<'offers' | 'materials'>(route.params?.target ?? 'offers');
  const [text, setText] = useState<string>(route.params?.text ?? '');
  const [resp, setResp] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const status = useApi<{ external_ai_enabled: boolean; message: string }>('/ai/status/');

  const run = async (t = text) => {
    if (t.trim().length < 3) {
      setError('اكتب طلبك بجملة واضحة.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResp(await api<Resp>('/ai/search/', { method: 'POST', body: { text: t, target } }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر تنفيذ البحث');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen>
      <Chips options={[{ value: 'offers', label: 'منتجات وخدمات' }, { value: 'materials', label: 'مواد خام' }]} value={target}
        onChange={(v) => { setTarget((v ?? 'offers') as any); setResp(null); }} />
      <Field multiline value={text} onChangeText={setText} placeholder="اكتب ما تحتاجه بكلماتك…" />
      <Button title="ابحث لي" icon="sparkles" loading={loading} onPress={() => run()} />
      {status.data ? <T size={12} color={colors.muted} center>{status.data.message}</T> : null}
      {!resp && !loading ? (
        <Card>
          <T weight="semibold">أمثلة:</T>
          {EXAMPLES[target].map((ex) => (
            <Button key={ex} title={ex} variant="secondary" small onPress={() => { setText(ex); run(ex); }} />
          ))}
          <T size={12} color={colors.muted}>
            المساعد يحوّل طلبك إلى شروط بحث ثم يبحث في العروض الحقيقية فقط، ولا يخترع أسعارًا أو كميات أو مواعيد.
          </T>
        </Card>
      ) : null}
      {error ? <ErrorView message={error} /> : null}
      {loading ? <Loading text="المساعد يفهم طلبك ويبحث…" /> : null}
      {resp && !loading ? (
        <>
          <Card>
            <Row style={{ justifyContent: 'space-between' }}>
              <T weight="bold">كيف فهمت طلبك</T>
              <Badge text={resp.source === 'ai' ? 'ذكاء اصطناعي' : 'قواعد مدمجة'} tone="gold" />
            </Row>
            <T size={13} weight="semibold">شروط إلزامية:</T>
            {resp.criteria.mandatory.length ? (
              <Row wrap gap={6}>{resp.criteria.mandatory.map((m) => <Badge key={m} text={m} tone="primary" />)}</Row>
            ) : <T size={13} color={colors.muted}>لا يوجد</T>}
            <T size={13} weight="semibold">تفضيلات مرنة:</T>
            {resp.criteria.preferences.length ? (
              <Row wrap gap={6}>{resp.criteria.preferences.map((m) => <Badge key={m} text={m} />)}</Row>
            ) : <T size={13} color={colors.muted}>لا يوجد</T>}
          </Card>
          <Notice text={resp.message} tone={resp.results.some((r) => r.match === 'full') ? 'success' : 'warning'} />
          {!resp.results.length ? <Empty title="لا توجد نتائج" subtitle="جرّب صياغة أخرى أو خفف الشروط." /> : null}
          {resp.results.map((r) => (
            <View key={r.item.id} style={{ gap: 6 }}>
              {target === 'offers' ? <OfferCard offer={r.item} /> : <MaterialCard m={r.item} />}
              <View style={{ paddingHorizontal: space.sm, gap: 2 }}>
                <Badge text={r.match === 'full' ? 'مطابق للشروط' : 'قريب من طلبك'} tone={r.match === 'full' ? 'success' : 'warning'} />
                {r.reasons.map((x) => (
                  <Row key={x} gap={4}><Ionicons name="checkmark" size={14} color={colors.success} /><T size={12} color={colors.success}>{x}</T></Row>
                ))}
                {r.unmet.map((x) => (
                  <Row key={x} gap={4}><Ionicons name="close" size={14} color={colors.danger} /><T size={12} color={colors.danger}>{x}</T></Row>
                ))}
              </View>
            </View>
          ))}
        </>
      ) : null}
    </Screen>
  );
}
