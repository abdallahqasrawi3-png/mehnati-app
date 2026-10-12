import React, { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Material, Offer } from './api/types';

/**
 * Two separate carts:
 *  - sales cart: products/services from ONE home business (customer orders)
 *  - materials cart: raw materials from ONE supplier (purchase orders)
 * Prices shown are for display only; the server recalculates everything.
 */
export type SalesLine = { offer: Offer; quantity: number };
export type MaterialLine = { material: Material; quantity: number };

type CartState = {
  sales: SalesLine[];
  materials: MaterialLine[];
  addOffer: (offer: Offer, qty: number) => { replaced: boolean };
  setOfferQty: (offerId: number, qty: number) => void;
  removeOffer: (offerId: number) => void;
  clearSales: () => void;
  addMaterial: (m: Material, qty: number) => { replaced: boolean };
  setMaterialQty: (id: number, qty: number) => void;
  removeMaterial: (id: number) => void;
  clearMaterials: () => void;
};

const Ctx = createContext<CartState>(null as any);
export const useCart = () => useContext(Ctx);
const KEY = 'mehnaty.cart.v1';

export function CartProvider({ children }: { children: ReactNode }) {
  const [sales, setSales] = useState<SalesLine[]>([]);
  const [materials, setMaterials] = useState<MaterialLine[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((raw) => {
        if (raw) {
          const d = JSON.parse(raw);
          setSales(d.sales ?? []);
          setMaterials(d.materials ?? []);
        }
      })
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  useEffect(() => {
    if (loaded) AsyncStorage.setItem(KEY, JSON.stringify({ sales, materials })).catch(() => {});
  }, [sales, materials, loaded]);

  const addOffer = (offer: Offer, qty: number) => {
    const replaced = sales.length > 0 && sales[0].offer.business.id !== offer.business.id;
    setSales((cur) => {
      let base = cur;
      if (cur.length && cur[0].offer.business.id !== offer.business.id) base = [];
      const existing = base.find((l) => l.offer.id === offer.id);
      if (existing) return base.map((l) => (l.offer.id === offer.id ? { ...l, quantity: l.quantity + qty, offer } : l));
      return [...base, { offer, quantity: qty }];
    });
    return { replaced };
  };

  const addMaterial = (material: Material, qty: number) => {
    const replaced = materials.length > 0 && materials[0].material.supplier.id !== material.supplier.id;
    setMaterials((cur) => {
      let base = cur;
      if (cur.length && cur[0].material.supplier.id !== material.supplier.id) base = [];
      const existing = base.find((l) => l.material.id === material.id);
      if (existing) return base.map((l) => (l.material.id === material.id ? { ...l, quantity: l.quantity + qty, material } : l));
      return [...base, { material, quantity: qty }];
    });
    return { replaced };
  };

  return (
    <Ctx.Provider
      value={{
        sales, materials, addOffer, addMaterial,
        setOfferQty: (id, q) => setSales((c) => c.map((l) => (l.offer.id === id ? { ...l, quantity: Math.max(1, q) } : l))),
        removeOffer: (id) => setSales((c) => c.filter((l) => l.offer.id !== id)),
        clearSales: () => setSales([]),
        setMaterialQty: (id, q) => setMaterials((c) => c.map((l) => (l.material.id === id ? { ...l, quantity: q } : l))),
        removeMaterial: (id) => setMaterials((c) => c.filter((l) => l.material.id !== id)),
        clearMaterials: () => setMaterials([]),
      }}
    >
      {children}
    </Ctx.Provider>
  );
}
