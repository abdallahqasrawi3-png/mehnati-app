import React from 'react';
import { View } from 'react-native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { useCart } from './cart';
import { colors, fonts } from './theme';
import { T } from './ui';

import HomeScreen from './screens/public/HomeScreen';
import SearchScreen from './screens/public/SearchScreen';
import SmartSearchScreen from './screens/public/SmartSearchScreen';
import OfferScreen from './screens/public/OfferScreen';
import BusinessScreen from './screens/public/BusinessScreen';
import CompareScreen from './screens/public/CompareScreen';
import MaterialsScreen from './screens/public/MaterialsScreen';
import MaterialScreen from './screens/public/MaterialScreen';
import SupplierScreen from './screens/public/SupplierScreen';
import CategoriesScreen from './screens/public/CategoriesScreen';
import LoginScreen from './screens/auth/LoginScreen';
import RegisterScreen from './screens/auth/RegisterScreen';
import CartScreen from './screens/cart/CartScreen';
import AccountScreen from './screens/account/AccountScreen';
import ProfileScreen from './screens/account/ProfileScreen';
import AddressesScreen from './screens/account/AddressesScreen';
import NotificationsScreen from './screens/account/NotificationsScreen';
import ContactAdminScreen from './screens/account/ContactAdminScreen';
import OrdersScreen from './screens/orders/OrdersScreen';
import OrderScreen from './screens/orders/OrderScreen';
import ShipmentsScreen from './screens/orders/ShipmentsScreen';
import ShipmentScreen from './screens/orders/ShipmentScreen';
import BusinessEditScreen from './screens/business/BusinessEditScreen';
import MyOffersScreen from './screens/business/MyOffersScreen';
import OfferEditScreen from './screens/business/OfferEditScreen';
import BusinessReportsScreen from './screens/business/BusinessReportsScreen';
import SupplierEditScreen from './screens/supplier/SupplierEditScreen';
import MyMaterialsScreen from './screens/supplier/MyMaterialsScreen';
import MaterialEditScreen from './screens/supplier/MaterialEditScreen';
import SupplierReportsScreen from './screens/supplier/SupplierReportsScreen';
import AdminScreen from './screens/admin/AdminScreen';

const Stack = createNativeStackNavigator();
const Tabs = createBottomTabNavigator();

const headerOptions = {
  headerStyle: { backgroundColor: colors.primary },
  headerTintColor: colors.white,
  headerTitleStyle: { fontFamily: fonts.bold, fontSize: 17 },
  headerTitleAlign: 'center' as const,
  contentStyle: { backgroundColor: colors.bg },
};

function CartIcon({ color, size }: { color: string; size: number }) {
  const { sales, materials } = useCart();
  const n = sales.length + materials.length;
  return (
    <View>
      <Ionicons name="bag-handle-outline" size={size} color={color} />
      {n > 0 ? (
        <View style={{ position: 'absolute', top: -4, right: -8, backgroundColor: colors.gold, borderRadius: 9, minWidth: 18, height: 18, alignItems: 'center', justifyContent: 'center' }}>
          <T size={10} color="#fff" weight="bold" center>{n}</T>
        </View>
      ) : null}
    </View>
  );
}

function MainTabs() {
  return (
    <Tabs.Navigator
      screenOptions={{
        ...headerOptions,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.muted,
        // Cairo is taller than the system font: give labels room so they are not clipped.
        tabBarLabelStyle: { fontFamily: fonts.semibold, fontSize: 11, lineHeight: 18 },
        tabBarStyle: { backgroundColor: colors.card, borderTopColor: colors.border, height: 68, paddingBottom: 10, paddingTop: 6 },
      }}
    >
      <Tabs.Screen name="Home" component={HomeScreen} options={{ title: 'الرئيسية', headerShown: false, tabBarIcon: (p) => <Ionicons name="home-outline" {...p} /> }} />
      <Tabs.Screen name="Search" component={SearchScreen} options={{ title: 'البحث', tabBarIcon: (p) => <Ionicons name="search-outline" {...p} /> }} />
      <Tabs.Screen name="Materials" component={MaterialsScreen} options={{ title: 'المواد الخام', tabBarIcon: (p) => <Ionicons name="layers-outline" {...p} /> }} />
      <Tabs.Screen name="Cart" component={CartScreen} options={{ title: 'السلة', tabBarIcon: (p) => <CartIcon {...p} /> }} />
      <Tabs.Screen name="Account" component={AccountScreen} options={{ title: 'حسابي', headerShown: false, tabBarIcon: (p) => <Ionicons name="person-circle-outline" {...p} /> }} />
    </Tabs.Navigator>
  );
}

export default function RootNavigator() {
  return (
    <Stack.Navigator screenOptions={headerOptions}>
      <Stack.Screen name="Main" component={MainTabs} options={{ headerShown: false, title: 'مهنتي' }} />
      <Stack.Screen name="SmartSearch" component={SmartSearchScreen} options={{ title: 'المساعد الذكي' }} />
      <Stack.Screen name="Categories" component={CategoriesScreen} options={{ title: 'التصنيفات' }} />
      <Stack.Screen name="Offer" component={OfferScreen} options={{ title: 'تفاصيل العرض' }} />
      <Stack.Screen name="Business" component={BusinessScreen} options={{ title: 'صفحة المشروع' }} />
      <Stack.Screen name="Compare" component={CompareScreen} options={{ title: 'المقارنة' }} />
      <Stack.Screen name="Material" component={MaterialScreen} options={{ title: 'تفاصيل المادة الخام' }} />
      <Stack.Screen name="Supplier" component={SupplierScreen} options={{ title: 'صفحة المورد' }} />
      <Stack.Screen name="Login" component={LoginScreen} options={{ title: 'تسجيل الدخول', headerShown: false }} />
      <Stack.Screen name="Register" component={RegisterScreen} options={{ title: 'إنشاء حساب' }} />
      <Stack.Screen name="Profile" component={ProfileScreen} options={{ title: 'بياناتي' }} />
      <Stack.Screen name="Addresses" component={AddressesScreen} options={{ title: 'عناويني' }} />
      <Stack.Screen name="Notifications" component={NotificationsScreen} options={{ title: 'الإشعارات' }} />
      <Stack.Screen name="ContactAdmin" component={ContactAdminScreen} options={{ title: 'تواصل مع الإدارة' }} />
      <Stack.Screen name="Orders" component={OrdersScreen} options={{ title: 'الطلبات' }} />
      <Stack.Screen name="Order" component={OrderScreen} options={{ title: 'تفاصيل الطلب' }} />
      <Stack.Screen name="Shipments" component={ShipmentsScreen} options={{ title: 'الشحنات' }} />
      <Stack.Screen name="Shipment" component={ShipmentScreen} options={{ title: 'تفاصيل الشحنة' }} />
      <Stack.Screen name="BusinessEdit" component={BusinessEditScreen} options={{ title: 'ملف المشروع' }} />
      <Stack.Screen name="MyOffers" component={MyOffersScreen} options={{ title: 'منتجاتي وخدماتي' }} />
      <Stack.Screen name="OfferEdit" component={OfferEditScreen} options={{ title: 'العرض' }} />
      <Stack.Screen name="BusinessReports" component={BusinessReportsScreen} options={{ title: 'التقارير المالية' }} />
      <Stack.Screen name="SupplierEdit" component={SupplierEditScreen} options={{ title: 'ملف المورد' }} />
      <Stack.Screen name="MyMaterials" component={MyMaterialsScreen} options={{ title: 'موادي الخام' }} />
      <Stack.Screen name="MaterialEdit" component={MaterialEditScreen} options={{ title: 'المادة الخام' }} />
      <Stack.Screen name="SupplierReports" component={SupplierReportsScreen} options={{ title: 'تقارير المورد' }} />
      <Stack.Screen name="Admin" component={AdminScreen} options={{ title: 'لوحة مدير المنصة' }} />
    </Stack.Navigator>
  );
}
