import React, { useEffect } from 'react';
import { I18nManager, Platform, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useFonts, Cairo_400Regular, Cairo_600SemiBold, Cairo_700Bold } from '@expo-google-fonts/cairo';
import * as SplashScreen from 'expo-splash-screen';
import { AuthProvider } from './src/auth';
import { CartProvider } from './src/cart';
import { ToastProvider } from './src/feedback';
import RootNavigator from './src/navigation';
import { colors } from './src/theme';
import { Loading } from './src/ui';

// Arabic-only app: right-to-left everywhere.
I18nManager.allowRTL(true);
I18nManager.forceRTL(true);
if (Platform.OS === 'web' && typeof document !== 'undefined') {
  document.documentElement.dir = 'rtl';
  document.documentElement.lang = 'ar';
  document.title = 'مهنتي';
}
SplashScreen.preventAutoHideAsync().catch(() => {});

// Web URLs (also make browser back/refresh work)
const linking = {
  prefixes: [],
  config: {
    screens: {
      Main: { screens: { Home: '', Search: 'search', Materials: 'materials', Cart: 'cart', Account: 'account' } },
      SmartSearch: 'assistant', Categories: 'categories', Offer: 'offer/:id', Business: 'business/:id',
      Compare: 'compare', Material: 'material/:id', Supplier: 'supplier/:id', Login: 'login', Register: 'register',
      Profile: 'profile', Addresses: 'addresses', Notifications: 'notifications', Orders: 'orders/:kind/:role',
      Order: 'order/:kind/:id', Shipments: 'shipments', Shipment: 'shipment/:id', BusinessEdit: 'my/business',
      MyOffers: 'my/offers', OfferEdit: 'my/offer/:id?', BusinessReports: 'my/reports', SupplierEdit: 'my/supplier',
      MyMaterials: 'my/materials', MaterialEdit: 'my/material/:id?', SupplierReports: 'my/supplier-reports', Admin: 'admin',
    },
  },
};

const theme = {
  ...DefaultTheme,
  colors: { ...DefaultTheme.colors, primary: colors.primary, background: colors.bg, card: colors.card, text: colors.text, border: colors.border },
};

export default function App() {
  const [fontsLoaded] = useFonts({ Cairo_400Regular, Cairo_600SemiBold, Cairo_700Bold });
  useEffect(() => {
    if (fontsLoaded) SplashScreen.hideAsync().catch(() => {});
  }, [fontsLoaded]);
  if (!fontsLoaded) {
    return (
      <View style={{ flex: 1, backgroundColor: colors.bg, justifyContent: 'center' }}>
        <Loading />
      </View>
    );
  }
  return (
    <SafeAreaProvider>
      <ToastProvider>
        <AuthProvider>
          <CartProvider>
            <NavigationContainer theme={theme} linking={linking as any} documentTitle={{
              // Site name first: «مهنتي · حسابي»; home shows the tagline.
              formatter: (o) => (!o?.title || o.title === 'الرئيسية' ? 'مهنتي · منصة تمكين المشاريع المنزلية' : `مهنتي · ${o.title}`),
            }}>
              <StatusBar style="light" />
              <RootNavigator />
            </NavigationContainer>
          </CartProvider>
        </AuthProvider>
      </ToastProvider>
    </SafeAreaProvider>
  );
}
