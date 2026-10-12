// Visual identity taken from the Mehnaty logo: deep green, warm gold, cream linen.
export const colors = {
  primary: '#1E5B3E',
  primaryDark: '#143F2B',
  primarySoft: '#E3EEE6',
  gold: '#B8925A',
  goldSoft: '#F3E9D8',
  bg: '#F7F2E8',
  card: '#FFFDF8',
  text: '#26302A',
  muted: '#6E746F',
  border: '#E6DCCB',
  danger: '#B3473A',
  dangerSoft: '#F8E3DF',
  success: '#2E7D4F',
  successSoft: '#E1F1E6',
  warning: '#B7791F',
  warningSoft: '#FBF0DA',
  white: '#FFFFFF',
};

export const fonts = {
  regular: 'Cairo_400Regular',
  semibold: 'Cairo_600SemiBold',
  bold: 'Cairo_700Bold',
};

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };
export const radius = { sm: 8, md: 12, lg: 18, pill: 999 };

export const shadow = {
  shadowColor: '#3B2F1E',
  shadowOpacity: 0.08,
  shadowRadius: 10,
  shadowOffset: { width: 0, height: 3 },
  elevation: 2,
};

export const CURRENCY = '₪';

export function money(v: string | number | null | undefined) {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return `${n.toLocaleString('ar-EG-u-nu-latn', { maximumFractionDigits: 2 })} ${CURRENCY}`;
}

export function qty(v: string | number | null | undefined) {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
}

export function dateText(v?: string | null) {
  if (!v) return '—';
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleDateString('ar-EG-u-nu-latn', { year: 'numeric', month: 'short', day: 'numeric' });
}

export function dateTimeText(v?: string | null) {
  if (!v) return '—';
  const d = new Date(v);
  return d.toLocaleString('ar-EG-u-nu-latn', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}
