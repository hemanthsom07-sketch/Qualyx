// Qualyx Demo Store — pure cart logic, deliberately separated from React
// so it can be unit-tested without a browser/DOM/React runtime.

import type { Product } from "./products";

export type CartState = Record<string, number>;

export function addToCart(cart: CartState, productId: string): CartState {
  return { ...cart, [productId]: (cart[productId] ?? 0) + 1 };
}

export function cartCount(cart: CartState): number {
  return Object.values(cart).reduce((sum, qty) => sum + qty, 0);
}

export function cartSubtotal(cart: CartState, products: Product[]): number {
  return Object.entries(cart).reduce((sum, [id, qty]) => {
    const product = products.find((p) => p.id === id);
    return product ? sum + product.price * qty : sum;
  }, 0);
}

export function clearCart(): CartState {
  return {};
}
