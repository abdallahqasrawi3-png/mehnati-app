import React, { createContext, ReactNode, useCallback, useContext, useRef, useState } from 'react';
import { Alert, Platform, Pressable, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, radius, shadow, space } from './theme';
import { Row, T } from './ui';

type Tone = 'success' | 'error' | 'info';
type ToastFn = (message: string, tone?: Tone) => void;

const ToastCtx = createContext<ToastFn>(() => {});

export function useToast() {
  return useContext(ToastCtx);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<{ message: string; tone: Tone } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const show = useCallback<ToastFn>((message, tone = 'success') => {
    setToast({ message, tone });
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setToast(null), tone === 'error' ? 5000 : 3000);
  }, []);
  const tone = toast?.tone ?? 'info';
  const bg = tone === 'success' ? colors.success : tone === 'error' ? colors.danger : colors.primaryDark;
  return (
    <ToastCtx.Provider value={show}>
      {children}
      {toast ? (
        <View pointerEvents="box-none" style={{ position: 'absolute', top: 12, left: 0, right: 0, alignItems: 'center', zIndex: 1000 }}>
          <Pressable onPress={() => setToast(null)} accessibilityRole="alert"
            style={{ backgroundColor: bg, borderRadius: radius.md, paddingVertical: space.sm, paddingHorizontal: space.lg, maxWidth: 560, marginHorizontal: space.lg, ...shadow }}>
            <Row>
              <Ionicons name={tone === 'success' ? 'checkmark-circle' : tone === 'error' ? 'alert-circle' : 'information-circle'} size={20} color="#fff" />
              <T color="#fff" weight="semibold" style={{ flexShrink: 1 }}>{toast.message}</T>
            </Row>
          </Pressable>
        </View>
      ) : null}
    </ToastCtx.Provider>
  );
}

/** Confirmation dialog that works in the browser and on phones. */
export function confirm(title: string, message = ''): Promise<boolean> {
  if (Platform.OS === 'web') {
    return Promise.resolve(globalThis.confirm ? globalThis.confirm(`${title}\n${message}`) : true);
  }
  return new Promise((resolve) => {
    Alert.alert(title, message, [
      { text: 'إلغاء', style: 'cancel', onPress: () => resolve(false) },
      { text: 'تأكيد', onPress: () => resolve(true) },
    ]);
  });
}
