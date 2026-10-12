import React, { useState } from 'react';
import { useNavigation } from '@react-navigation/native';
import { api, ApiError } from './api/client';
import { useAuth } from './auth';
import { useToast } from './feedback';
import { colors } from './theme';
import { Button, Card, Field, T } from './ui';

/** Report content (offer, business, review, material, supplier) to the platform admins. */
export default function ReportAbuse({ type, id }: { type: string; id: number }) {
  const { me } = useAuth();
  const nav = useNavigation<any>();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  if (!open) {
    return <Button title="الإبلاغ عن محتوى مخالف" icon="flag-outline" variant="ghost" small onPress={() => (me ? setOpen(true) : nav.navigate('Login'))} />;
  }
  const send = async () => {
    if (reason.trim().length < 5) {
      toast('اكتب سبب البلاغ بوضوح.', 'error');
      return;
    }
    try {
      await api('/abuse-reports/', { method: 'POST', body: { target_type: type, target_id: id, reason } });
      toast('تم إرسال البلاغ إلى إدارة المنصة. شكرًا لك.');
      setOpen(false);
      setReason('');
    } catch (e) {
      toast(e instanceof ApiError ? e.message : 'تعذر إرسال البلاغ', 'error');
    }
  };
  return (
    <Card>
      <T weight="semibold">سبب البلاغ</T>
      <Field multiline value={reason} onChangeText={setReason} placeholder="صف المشكلة باختصار" />
      <T size={12} color={colors.muted}>تراجع إدارة المنصة البلاغ وتتخذ الإجراء المناسب.</T>
      <Button title="إرسال البلاغ" variant="danger" onPress={send} />
      <Button title="إلغاء" variant="ghost" small onPress={() => setOpen(false)} />
    </Card>
  );
}
