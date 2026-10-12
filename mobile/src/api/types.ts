export type Me = {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  city: number | null;
  city_name: string | null;
  roles: string[];
  is_staff: boolean;
  business_profile_id: number | null;
  supplier_profile_id: number | null;
};

export type Category = { id: number; name: string; kind: 'offer' | 'material'; icon: string };
export type Area = { id: number; name: string };
export type City = { id: number; name: string; areas: Area[] };
export type Img = { id: number; image: string };

export type BusinessCard = {
  id: number;
  name: string;
  city_name: string;
  area_name: string | null;
  rating_avg: string;
  rating_count: number;
  pickup_available: boolean;
  delivery_available: boolean;
  logo: string | null;
};

export type Offer = {
  id: number;
  title: string;
  description: string;
  category: Category;
  offer_type: 'ready' | 'made_to_order' | 'service';
  offer_type_display: string;
  price: string;
  price_unit: string;
  preparation_days: number;
  service_duration: string;
  is_available: boolean;
  available_quantity: number | null;
  is_orderable: boolean;
  images: Img[];
  business: BusinessCard;
};

export type SupplierCard = {
  id: number;
  name: string;
  city_name: string;
  area_name: string | null;
  pickup_available: boolean;
  delivery_available: boolean;
  delivery_cost: string | null;
  delivery_days: number | null;
  logo: string | null;
};

export type Material = {
  id: number;
  title: string;
  description: string;
  specifications: string;
  category: Category;
  unit: string;
  unit_display: string;
  price: string;
  available_quantity: string;
  min_order_quantity: string;
  preparation_days: number;
  is_available: boolean;
  images: Img[];
  supplier: SupplierCard;
};

export type Paged<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export type Address = {
  id: number;
  label: string;
  recipient_name: string;
  phone: string;
  city: number;
  city_name: string;
  area: number | null;
  area_name: string | null;
  street: string;
  building: string;
  floor: string;
  apartment: string;
  landmark: string;
  details: string;
  latitude: number | null;
  longitude: number | null;
  full_text: string;
  map_url: string | null;
};
