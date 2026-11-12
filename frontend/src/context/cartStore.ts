import { createContext } from "react";
import type { CartResponse, Product } from "../types";

export type CartContextValue = {
  cart: CartResponse;
  cartError: string;
  refresh: () => Promise<void>;
  add: (product: Product, quantity?: number) => Promise<void>;
  save: (lines: Array<{ product: Product; quantity: number }>) => Promise<CartResponse>;
  setQuantity: (itemId: number, quantity: number) => Promise<void>;
  remove: (itemId: number) => Promise<void>;
  count: number;
};

export const CartContext = createContext<CartContextValue | null>(null);
