import React, { useState } from 'react';
import { Image } from 'react-native';
import { ApiError } from '../../api/client';
import { useAuth } from '../../auth';
import { useToast } from '../../feedback';
import { colors, radius } from '../../theme';
import { Button, Card, ErrorView, Field, Screen, T } from '../../ui';

export default function LoginScreen({ navigation }: any) {
  const { login } = useAuth();
  const toast = useToast();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setError(null);
    if (!email.includes('@') || password.length < 1) {
      setError('أدخل البريد الإلكتروني وكلمة المرور.');
      return;
    }
    try {
      await login(email, password);
      toast('تم تسجيل الدخول.');
      navigation.goBack();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'تعذر تسجيل الدخول');
    }
  };

  return (
    <Screen style={{ maxWidth: 480 }}>
      <Image source={require('../../../assets/wordmark.jpg')} style={{ width: '100%', height: 120, borderRadius: radius.lg }} resizeMode="contain" />
      <Card>
        <Field label="البريد الإلكتروني" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" autoComplete="email" textContentType="emailAddress" />
        <Field label="كلمة المرور" value={password} onChangeText={setPassword} secureTextEntry autoComplete="password" onSubmitEditing={submit} />
        {error ? <ErrorView message={error} /> : null}
        <Button title="دخول" onPress={submit} />
      </Card>
      <T center color={colors.muted}>ليس لديك حساب؟</T>
      <Button title="إنشاء حساب جديد" variant="outline" onPress={() => navigation.replace('Register')} />
    </Screen>
  );
}
