import React, { useState } from 'react';
import { Linking, View } from 'react-native';
import { api, ApiError, SERVER_URL } from '../../api/client';
import { Paged } from '../../api/types';
import { StatTile } from '../../charts';
import { confirm, useToast } from '../../feedback';
import { useApi } from '../../hooks';
import { colors, dateText, money, space } from '../../theme';
import { Badge, Button, Card, Chips, Empty, ErrorView, Field, KV, Loading, Notice, Row, Screen, SectionTitle, T } from '../../ui';

const SALES_LABELS: Record<string, string> = {
  pending: 'بانتظار القبول', accepted: 'مقبول', preparing: 'قيد التجهيز', ready: 'جاهز', in_transit: 'في الطريق',
  completed: 'مكتمل', rejected: 'مرفوض', cancelled: 'ملغى', delivery_failed: 'تعذر التسليم', shipped: 'مشحون', received: 'مستلم',
};

function Indicators() {
  const { data: d, error, loading, reload } = useApi<any>('/reports/admin/');
  if (loading && !d) return <Loading />;
  if (error || !d) return <ErrorView message={error ?? ''} onRetry={reload} />;
  return (
    <>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
        <StatTile count label="المستخدمون" value={d.users} note={`${d.active_users} فعّال`} />
        <StatTile count label="المشاريع المنزلية" value={d.businesses} />
        <StatTile count label="الموردون" value={d.suppliers} />
        <StatTile count label="العروض / المواد" value={`${d.offers} / ${d.materials}` as any} />
        <StatTile label="قيمة المبيعات المكتملة" value={d.completed_sales_value} />
        <StatTile count label="بلاغات مفتوحة" value={d.open_abuse_reports} />
      </View>
      <Card>
        <T weight="bold">طلبات البيع حسب الحالة</T>
        {Object.entries(d.sales_orders_by_status).map(([k, v]) => <KV key={k} k={SALES_LABELS[k] ?? k} v={String(v)} />)}
        <T weight="bold">طلبات الشراء حسب الحالة</T>
        {Object.entries(d.purchase_orders_by_status).map(([k, v]) => <KV key={k} k={SALES_LABELS[k] ?? k} v={String(v)} />)}
      </Card>
    </>
  );
}

function ContactMessages() {
  const toast = useToast();
  const [status, setStatus] = useState('open');
  const { data, error, loading, reload } = useApi<Paged<any>>('/admin/contact-messages/', { status });
  const resolve = async (id: number) => {
    if (!(await confirm('تعليم الرسالة كمعالجة؟'))) return;
    try {
      await api(`/admin/contact-messages/${id}/resolve/`, { method: 'POST', body: {} });
      toast('تم تحديث الرسالة.');
      reload();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر التحديث', 'error');
    }
  };
  const wa = (phone: string) => `https://wa.me/${phone.replace(/\D/g, '').replace(/^0/, '970')}`;
  return (
    <>
      <Chips options={[{ value: 'open', label: 'جديدة' }, { value: 'resolved', label: 'معالجة' }]} value={status} onChange={(v) => v && setStatus(v)} />
      {loading && !data ? <Loading /> : error ? <ErrorView message={error} onRetry={reload} /> : !data?.results.length ? (
        <Empty icon="chatbubbles-outline" title="لا توجد رسائل" />
      ) : data.results.map((m) => (
        <Card key={m.id}>
          <Row style={{ justifyContent: 'space-between' }}>
            <T weight="bold">#{m.id} · {m.kind_display}</T>
            <Badge text={m.status_display} tone={m.status === 'open' ? 'warning' : 'success'} />
          </Row>
          <T>{m.message}</T>
          <T size={12} color={colors.muted}>
            {m.name}{m.phone ? ` · ${m.phone}` : ''}{m.email ? ` · ${m.email}` : ''}{m.order_ref ? ` · طلب #${m.order_ref}` : ''} · {dateText(m.created_at)}
          </T>
          <Row wrap>
            {m.phone ? <Button small variant="outline" icon="logo-whatsapp" title="مراسلة المُبلِّغ" onPress={() => Linking.openURL(wa(m.phone))} /> : null}
            {m.status === 'open' ? <Button small title="تمت المعالجة" icon="checkmark-done-outline" onPress={() => resolve(m.id)} /> : null}
          </Row>
        </Card>
      ))}
    </>
  );
}

function Reports() {
  const toast = useToast();
  const [status, setStatus] = useState('open');
  const { data, error, loading, reload } = useApi<Paged<any>>('/admin/abuse-reports/', { status });
  const resolve = async (id: number, decision: string, hide: boolean) => {
    if (!(await confirm(decision === 'dismissed' ? 'رفض البلاغ؟' : hide ? 'قبول البلاغ وإخفاء/إيقاف المحتوى؟' : 'تعليم البلاغ كمعالج؟'))) return;
    try {
      await api(`/admin/abuse-reports/${id}/resolve/`, { method: 'POST', body: { decision, hide_content: hide } });
      toast('تم تحديث البلاغ.');
      reload();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر التحديث', 'error');
    }
  };
  return (
    <>
      <Chips options={[{ value: 'open', label: 'مفتوحة' }, { value: 'resolved', label: 'معالجة' }, { value: 'dismissed', label: 'مرفوضة' }]} value={status} onChange={(v) => v && setStatus(v)} />
      {loading && !data ? <Loading /> : error ? <ErrorView message={error} /> : !data?.results.length ? <Empty icon="flag-outline" title="لا توجد بلاغات" /> :
        data.results.map((r) => (
          <Card key={r.id}>
            <Row style={{ justifyContent: 'space-between' }}>
              <T weight="bold">{r.target_type_display} #{r.target_id}</T>
              <Badge text={r.status_display} tone={r.status === 'open' ? 'warning' : 'neutral'} />
            </Row>
            <T>{r.reason}</T>
            {r.target ? <T size={12} color={colors.muted}>المحتوى: {JSON.stringify(r.target).replace(/[{}"]/g, ' ')}</T> : <T size={12} color={colors.muted}>المحتوى لم يعد موجودًا.</T>}
            <T size={12} color={colors.muted}>{dateText(r.created_at)}</T>
            {r.status === 'open' ? (
              <Row wrap>
                <Button small variant="danger" title="قبول وإخفاء المحتوى" onPress={() => resolve(r.id, 'resolved', true)} />
                <Button small variant="outline" title="معالج دون إخفاء" onPress={() => resolve(r.id, 'resolved', false)} />
                <Button small variant="ghost" title="رفض البلاغ" onPress={() => resolve(r.id, 'dismissed', false)} />
              </Row>
            ) : null}
          </Card>
        ))}
    </>
  );
}

function Users() {
  const toast = useToast();
  const [q, setQ] = useState('');
  const { data, loading, reload } = useApi<Paged<any>>('/admin/users/', { q });
  const profiles = useApi<any[]>('/admin/profiles/profiles/');
  const setActive = async (u: any) => {
    if (!(await confirm(u.is_active ? `إيقاف حساب ${u.email}؟` : `إعادة تفعيل ${u.email}؟`))) return;
    try {
      await api(`/admin/users/${u.id}/set_active/`, { method: 'POST', body: { is_active: !u.is_active } });
      reload();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر التحديث', 'error');
    }
  };
  const setProfile = async (p: any) => {
    const next = p.status === 'active' ? 'suspended' : 'active';
    if (!(await confirm(next === 'suspended' ? `إيقاف «${p.name}»؟` : `تفعيل «${p.name}»؟`))) return;
    await api(`/admin/profiles/${p.kind}/${p.id}/`, { method: 'POST', body: { status: next } });
    profiles.reload();
  };
  return (
    <>
      <Field value={q} onChangeText={setQ} placeholder="ابحث بالبريد أو الاسم" />
      {loading && !data ? <Loading /> : data?.results.map((u) => (
        <Card key={u.id}>
          <Row style={{ justifyContent: 'space-between' }}>
            <View style={{ flex: 1 }}>
              <T weight="semibold">{u.full_name}</T>
              <T size={12} color={colors.muted}>{u.email} · {u.roles.join('، ')}</T>
            </View>
            {u.is_staff ? <Badge text="مدير" tone="gold" /> : (
              <Button small variant={u.is_active ? 'outline' : 'primary'} title={u.is_active ? 'إيقاف' : 'تفعيل'} onPress={() => setActive(u)} />
            )}
          </Row>
        </Card>
      ))}
      <SectionTitle title="ملفات المشاريع والموردين" />
      {profiles.data?.map((p) => (
        <Card key={`${p.kind}${p.id}`}>
          <Row style={{ justifyContent: 'space-between' }}>
            <View style={{ flex: 1 }}>
              <T weight="semibold">{p.name}</T>
              <T size={12} color={colors.muted}>{p.kind === 'business' ? 'مشروع منزلي' : 'مورد'} · {p.owner}</T>
            </View>
            <Badge text={p.status === 'active' ? 'فعّال' : 'موقوف'} tone={p.status === 'active' ? 'success' : 'danger'} />
            <Button small variant="outline" title={p.status === 'active' ? 'إيقاف' : 'تفعيل'} onPress={() => setProfile(p)} />
          </Row>
        </Card>
      ))}
    </>
  );
}

export default function AdminScreen() {
  const [tab, setTab] = useState('indicators');
  return (
    <Screen>
      <Chips options={[{ value: 'indicators', label: 'المؤشرات' }, { value: 'reports', label: 'البلاغات' }, { value: 'contact', label: 'رسائل التواصل' }, { value: 'users', label: 'الحسابات' }]} value={tab} onChange={(v) => v && setTab(v)} />
      {tab === 'indicators' ? <Indicators /> : tab === 'reports' ? <Reports /> : tab === 'contact' ? <ContactMessages /> : <Users />}
      <Notice text="لإدارة التصنيفات والمدن وشركات التوصيل وسجل العمليات الإدارية استخدم لوحة Django الإدارية." />
      <Button variant="outline" icon="open-outline" title="فتح لوحة الإدارة (Django)" onPress={() => Linking.openURL(`${SERVER_URL}/admin/`)} />
    </Screen>
  );
}
