import React, { useState } from 'react';
import { View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api, ApiError } from '../../api/client';
import { Paged } from '../../api/types';
import { BarList, StatTile } from '../../charts';
import { confirm, useToast } from '../../feedback';
import { useApi } from '../../hooks';
import { colors, dateText, money, space } from '../../theme';
import { Badge, Button, Card, Chips, Empty, ErrorView, Field, KV, Loading, Notice, Row, Screen, SectionTitle, T } from '../../ui';

const PERIODS = [{ value: 'day', label: 'اليوم' }, { value: 'week', label: 'الأسبوع' }, { value: 'month', label: 'الشهر' }];
const EXP_CATS = [
  { value: 'packaging', label: 'تغليف' }, { value: 'delivery', label: 'توصيل' }, { value: 'commission', label: 'عمولات' },
  { value: 'materials_used', label: 'مواد مستهلكة' }, { value: 'other', label: 'أخرى' },
];

function Expenses({ onChange }: { onChange: () => void }) {
  const toast = useToast();
  const list = useApi<Paged<any>>('/expenses/');
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ date: today, category: 'packaging', amount: '', note: '' });
  const add = async () => {
    try {
      await api('/expenses/', { method: 'POST', body: form });
      setForm({ ...form, amount: '', note: '' });
      toast('تم تسجيل المصروف.');
      list.reload();
      onChange();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر الحفظ', 'error');
    }
  };
  const del = async (id: number) => {
    if (!(await confirm('حذف المصروف؟'))) return;
    await api(`/expenses/${id}/`, { method: 'DELETE' });
    list.reload();
    onChange();
  };
  return (
    <Card>
      <T weight="bold">تسجيل مصروف مباشر</T>
      <Chips options={EXP_CATS} value={form.category} onChange={(v) => v && setForm({ ...form, category: v })} />
      <Row>
        <View style={{ flex: 1 }}><Field label="المبلغ ₪" value={form.amount} onChangeText={(v) => setForm({ ...form, amount: v })} keyboardType="decimal-pad" /></View>
        <View style={{ flex: 1 }}><Field label="التاريخ" value={form.date} onChangeText={(v) => setForm({ ...form, date: v })} /></View>
      </Row>
      <Field value={form.note} onChangeText={(v) => setForm({ ...form, note: v })} placeholder="ملاحظة" />
      <Button title="إضافة المصروف" variant="outline" onPress={add} disabled={!form.amount} />
      {list.data?.results.slice(0, 20).map((e) => (
        <Row key={e.id} style={{ justifyContent: 'space-between' }}>
          <T size={13}>{dateText(e.date)} · {e.category_display}{e.note ? ` · ${e.note}` : ''}</T>
          <Row gap={4}>
            <T size={13} weight="semibold">{money(e.amount)}</T>
            <Ionicons name="trash-outline" size={16} color={colors.danger} onPress={() => del(e.id)} accessibilityLabel="حذف" />
          </Row>
        </Row>
      ))}
    </Card>
  );
}

export default function BusinessReportsScreen() {
  const [period, setPeriod] = useState('month');
  const { data: r, error, loading, reload } = useApi<any>('/reports/business/', { period });
  const [summary, setSummary] = useState<{ summary: string; source: string } | null>(null);
  const toast = useToast();
  const summarize = async () => {
    try {
      setSummary(await api('/ai/business-summary/', { params: { period } }));
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر التلخيص', 'error');
    }
  };

  return (
    <Screen refreshing={loading} onRefresh={reload}>
      <Chips options={PERIODS} value={period} onChange={(v) => { if (v) { setPeriod(v); setSummary(null); } }} />
      {loading && !r ? <Loading /> : error ? <ErrorView message={error} onRetry={reload} /> : r ? (
        <>
          <T size={13} color={colors.muted}>{r.period.label}: {dateText(r.period.start)} – {dateText(r.period.end)}</T>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
            <StatTile label="إيرادات الطلبات المكتملة" value={r.revenue} note={`${r.completed_orders} طلب مكتمل`} />
            <StatTile label="تكلفة المباع" value={r.cost_of_goods_sold} note={r.items_missing_cost ? `${r.items_missing_cost} عنصر بلا تكلفة` : undefined} />
            <StatTile label="المصاريف المباشرة" value={(Number(r.expenses_total) + Number(r.delivery_paid_by_business)).toFixed(2)} note={Number(r.delivery_paid_by_business) ? `منها توصيل ${money(r.delivery_paid_by_business)}` : undefined} />
            <StatTile label="صافي الربح التشغيلي التقديري" value={r.estimated_operating_profit} emphasis />
          </View>
          {r.costs_incomplete ? <Notice tone="warning" text="التكاليف المسجلة ناقصة، لذلك الربح المعروض أعلى من الفعلي على الأرجح. أضف تكلفة الوحدة لعروضك." /> : null}
          <Card>
            <T size={12} color={colors.muted}>{r.formula}</T>
            {r.notes.map((n: string) => <T key={n} size={12} color={colors.muted}>• {n}</T>)}
          </Card>

          <Card>
            <Row style={{ justifyContent: 'space-between' }}>
              <Row><Ionicons name="sparkles" size={18} color={colors.gold} /><T weight="bold">ملخص المساعد</T></Row>
              {summary ? <Badge text={summary.source === 'ai' ? 'ذكاء اصطناعي' : 'قالب مدمج'} tone="gold" /> : null}
            </Row>
            {summary ? <T>{summary.summary}</T> : <T size={13} color={colors.muted}>يلخص أرقامك الحقيقية (الأرقام محسوبة بالنظام وليس بالذكاء الاصطناعي).</T>}
            <Button small variant="gold" title={summary ? 'تحديث الملخص' : 'لخّص لي'} onPress={summarize} />
          </Card>

          <SectionTitle title="الإيرادات اليومية" />
          <Card>
            {r.daily.length ? (
              <BarList rows={r.daily.map((d: any) => ({ label: dateText(d.date).replace(/ \d{4}$/, ''), value: Number(d.revenue), detail: `${d.orders} طلب مكتمل` }))} />
            ) : <Empty icon="bar-chart-outline" title="لا توجد مبيعات مكتملة في هذه الفترة" />}
          </Card>

          <SectionTitle title="الأكثر مبيعًا" />
          <Card>
            {r.best_sellers.length ? r.best_sellers.map((b: any, i: number) => (
              <KV key={b.title} k={`${i + 1}. ${b.title}`} v={`${b.quantity} · ${money(b.revenue)}`} />
            )) : <T color={colors.muted}>لا يوجد بعد.</T>}
          </Card>

          <SectionTitle title="مؤشرات أخرى" />
          <Card>
            <KV k="طلبات مفتوحة الآن" v={String(r.open_orders)} />
            <KV k="عناصر بمخزون منخفض" v={String(r.low_stock_items)} />
            <KV k="مشتريات مواد خام مستلمة (منفصلة)" v={`${money(r.raw_material_purchases.total)} · ${r.raw_material_purchases.received_orders} طلب`} />
          </Card>
          <Expenses onChange={reload} />
        </>
      ) : null}
    </Screen>
  );
}
