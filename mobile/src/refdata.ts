import { useEffect, useState } from 'react';
import { api } from './api/client';
import { Category, City } from './api/types';

let cache: { categories?: Category[]; cities?: City[] } = {};
let pending: Promise<void> | null = null;

async function loadAll() {
  const [categories, cities] = await Promise.all([api<Category[]>('/categories/'), api<City[]>('/cities/')]);
  cache = { categories, cities };
}

/** Categories and cities, fetched once and shared by all screens. */
export function useRefData() {
  const [state, setState] = useState(cache);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (cache.categories && cache.cities) return;
    pending = pending ?? loadAll();
    pending
      .then(() => setState({ ...cache }))
      .catch((e) => {
        pending = null;
        setError(e?.message ?? 'تعذر تحميل البيانات');
      });
  }, []);
  const categories = state.categories ?? [];
  const cities = state.cities ?? [];
  return {
    categories,
    offerCategories: categories.filter((c) => c.kind === 'offer'),
    materialCategories: categories.filter((c) => c.kind === 'material'),
    cities,
    error,
    loaded: !!(state.categories && state.cities),
  };
}

export const OFFER_TYPES = [
  { value: 'ready', label: 'منتج جاهز' },
  { value: 'made_to_order', label: 'حسب الطلب' },
  { value: 'service', label: 'خدمة' },
];

export const UNITS = [
  { value: 'piece', label: 'قطعة' },
  { value: 'meter', label: 'متر' },
  { value: 'kg', label: 'كيلوغرام' },
  { value: 'gram', label: 'غرام' },
  { value: 'pack', label: 'عبوة' },
  { value: 'roll', label: 'لفة' },
  { value: 'liter', label: 'لتر' },
  { value: 'box', label: 'صندوق' },
];

export const CATEGORY_ICONS: Record<string, string> = {
  'تطريز': 'flower-outline', 'خياطة': 'cut-outline', 'رسم': 'color-palette-outline', 'أعمال يدوية': 'hand-left-outline',
  'هدايا': 'gift-outline', 'مأكولات منزلية': 'restaurant-outline', 'تجميل': 'sparkles-outline', 'أقمشة': 'layers-outline',
  'خيوط': 'git-branch-outline', 'أدوات خياطة وتطريز': 'construct-outline', 'مكونات طعام': 'nutrition-outline',
  'مستلزمات تغليف': 'cube-outline',
};
