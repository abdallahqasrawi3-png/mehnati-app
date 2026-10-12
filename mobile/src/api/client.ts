import { Platform } from 'react-native';
import Constants from 'expo-constants';
import { getItem, setItem } from './storage';

function resolveApiUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  if (fromEnv) return fromEnv.replace(/\/$/, '');
  const port = process.env.EXPO_PUBLIC_API_PORT || '8000'; // set by start.ps1
  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:${port}/api`;
  }
  // On a phone running Expo Go, the dev machine's LAN address is in hostUri.
  const host = Constants.expoConfig?.hostUri?.split(':')[0];
  return host ? `http://${host}:${port}/api` : `http://10.0.2.2:${port}/api`;
}

export const API_URL = resolveApiUrl();
export const SERVER_URL = API_URL.replace(/\/api$/, '');

const ACCESS = 'mehnaty.access';
const REFRESH = 'mehnaty.refresh';

let access: string | null = null;
let refresh: string | null = null;
let onLogout: (() => void) | null = null;

export async function loadTokens() {
  access = await getItem(ACCESS);
  refresh = await getItem(REFRESH);
  return !!refresh;
}

export async function saveTokens(a: string | null, r: string | null) {
  access = a;
  refresh = r;
  await setItem(ACCESS, a);
  await setItem(REFRESH, r);
}

export function getRefreshToken() {
  return refresh;
}

export function setLogoutHandler(fn: () => void) {
  onLogout = fn;
}

export class ApiError extends Error {
  status: number;
  data: any;
  constructor(message: string, status: number, data: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

const FIELD_NAMES: Record<string, string> = {
  email: 'البريد', password: 'كلمة المرور', full_name: 'الاسم', title: 'العنوان', price: 'السعر',
  category: 'التصنيف', city: 'المدينة', area: 'المنطقة', name: 'الاسم', image: 'الصورة', quantity: 'الكمية',
  items: 'العناصر', order: 'الطلب', rating: 'التقييم', details: 'العنوان', phone: 'الهاتف', status: 'الحالة',
  delta: 'الكمية', amount: 'المبلغ', date: 'التاريخ', unit: 'الوحدة', non_field_errors: '',
};

export function errorMessage(data: any, status?: number): string {
  if (!data) return status === 0 ? 'تعذر الاتصال بالخادم. تأكد من تشغيله ومن الاتصال بالشبكة.' : 'حدث خطأ غير متوقع.';
  if (typeof data === 'string') return data;
  if (data.detail) return String(data.detail);
  if (Array.isArray(data)) return data.map((d) => errorMessage(d)).join('\n');
  if (typeof data === 'object') {
    return Object.entries(data)
      .map(([k, v]) => {
        const label = FIELD_NAMES[k] ?? k;
        const msg = Array.isArray(v) ? v.map((x) => (typeof x === 'object' ? errorMessage(x) : x)).join('، ') : errorMessage(v);
        return label ? `${label}: ${msg}` : msg;
      })
      .join('\n');
  }
  return 'حدث خطأ غير متوقع.';
}

async function tryRefresh(): Promise<boolean> {
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_URL}/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    await saveTokens(data.access, data.refresh ?? refresh);
    return true;
  } catch {
    return false;
  }
}

type Options = { method?: string; body?: any; params?: Record<string, any>; form?: FormData; auth?: boolean };

export async function api<T = any>(path: string, opts: Options = {}, retried = false): Promise<T> {
  const { method = 'GET', body, params, form } = opts;
  let url = `${API_URL}${path.startsWith('/') ? path : '/' + path}`;
  if (params) {
    const qs = Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== null && v !== '' && v !== false)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
      .join('&');
    if (qs) url += (url.includes('?') ? '&' : '?') + qs;
  }
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (access) headers.Authorization = `Bearer ${access}`;
  let payload: any;
  if (form) payload = form;
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }
  let res: Response;
  try {
    res = await fetch(url, { method, headers, body: payload });
  } catch {
    throw new ApiError(errorMessage(null, 0), 0, null);
  }
  if (res.status === 401 && !retried && refresh) {
    if (await tryRefresh()) return api<T>(path, opts, true);
    await saveTokens(null, null);
    onLogout?.();
  }
  if (res.status === 204) return undefined as T;
  let data: any = null;
  const text = await res.text();
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!res.ok) {
    let msg = errorMessage(data, res.status);
    if (res.status === 401 && !data?.detail) msg = 'يجب تسجيل الدخول.';
    if (res.status === 404 && (!data || data.detail === 'No Offer matches the given query.')) msg = 'العنصر غير موجود.';
    if (res.status === 429) msg = 'طلبات كثيرة. انتظر قليلًا ثم حاول مجددًا.';
    if (res.status >= 500) msg = 'حدث خطأ في الخادم. حاول لاحقًا.';
    throw new ApiError(msg, res.status, data);
  }
  return data as T;
}

export function imageUrl(path?: string | null): string | undefined {
  if (!path) return undefined;
  if (path.startsWith('http')) return path;
  return `${SERVER_URL}${path}`;
}

export async function uploadImage(path: string, uri: string, field = 'image') {
  const form = new FormData();
  if (Platform.OS === 'web') {
    const blob = await (await fetch(uri)).blob();
    const ext = blob.type.split('/')[1] || 'jpg';
    form.append(field, blob, `upload.${ext === 'jpeg' ? 'jpg' : ext}`);
  } else {
    const name = uri.split('/').pop() || 'upload.jpg';
    const ext = (name.split('.').pop() || 'jpg').toLowerCase();
    // @ts-ignore React Native file object
    form.append(field, { uri, name, type: `image/${ext === 'jpg' ? 'jpeg' : ext}` });
  }
  return api(path, { method: 'POST', form });
}
