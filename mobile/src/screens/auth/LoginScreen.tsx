import React, { useState } from 'react';
import { ApiError } from '../../api/client';
import { useAuth } from '../../auth';
import { useToast } from '../../feedback';
import { Button } from '../../ui';
import { AuthLayout, FormError, IconField, SwitchLink } from './AuthLayout';

export default function LoginScreen({ navigation }: any) {
  const { login } = useAuth();
  const toast = useToast();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const leave = () => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('Main', { screen: 'Home' }));

  const submit = async () => {
    setError(null);
    if (!email.includes('@') || password.length < 1) {
      setError('أدخل البريد الإلكتروني وكلمة المرور.');
      return;
    }
    setBusy(true);
    try {
      await login(email, password);
      toast('أهلًا بعودتك! تم تسجيل الدخول.');
      leave();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر تسجيل الدخول');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout title="مرحبًا بعودتك" subtitle="سجّل الدخول لمتابعة طلباتك ومشروعك." onBack={leave}>
      <IconField
        label="البريد الإلكتروني" icon="mail-outline" value={email} onChangeText={setEmail} placeholder="name@example.com"
        autoCapitalize="none" keyboardType="email-address" autoComplete="email" textContentType="emailAddress"
        returnKeyType="next" error={!!error && !email.includes('@')}
      />
      <IconField
        label="كلمة المرور" icon="lock-closed-outline" secure value={password} onChangeText={setPassword} placeholder="••••••••"
        autoComplete="password" textContentType="password" returnKeyType="go" onSubmitEditing={submit}
        error={!!error && !password}
      />
      {error ? <FormError message={error} /> : null}
      <Button title="تسجيل الدخول" icon="log-in-outline" loading={busy} onPress={submit} />
      <SwitchLink question="ليس لديك حساب؟" action="أنشئ حسابًا جديدًا" onPress={() => navigation.replace('Register')} />
    </AuthLayout>
  );
}
