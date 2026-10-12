import * as Location from 'expo-location';

import { Pin } from './coords';

export { parseCoordinates } from './coords';
export type { Pin } from './coords';

/** One-shot current position (asks permission). Throws an Arabic message on failure. */
export async function currentPosition(): Promise<Pin> {
  let perm;
  try {
    perm = await Location.requestForegroundPermissionsAsync();
  } catch {
    throw new Error('تحديد الموقع غير متاح على هذا الجهاز أو المتصفح.');
  }
  if (perm.status !== 'granted') throw new Error('لم يتم السماح بالوصول إلى الموقع. فعّله من إعدادات الجهاز أو الصق رابط الموقع.');
  try {
    const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
    return { latitude: loc.coords.latitude, longitude: loc.coords.longitude, accuracy: loc.coords.accuracy };
  } catch {
    throw new Error('تعذر تحديد موقعك الآن. تأكد من تشغيل GPS وحاول مجددًا.');
  }
}

export function mapLink(lat: number | string, lng: number | string) {
  return `https://www.google.com/maps?q=${lat},${lng}`;
}
