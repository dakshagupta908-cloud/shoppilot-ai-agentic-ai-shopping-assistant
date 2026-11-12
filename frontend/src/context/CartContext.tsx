import { useCallback, useEffect, useMemo, useState } from "react";
import { api, errorMessage } from "../services/api";
import type { CartLineInput, CartResponse, Product } from "../types";
import { CartContext } from "./cartStore";

const emptyCart: CartResponse = { session_id: "", items: [], subtotal: 0, total: 0, currency: "INR" };

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [cart, setCart] = useState<CartResponse>(emptyCart);
  const [cartError, setCartError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get<CartResponse>("/api/cart");
      setCart(data);
      setCartError("");
    } catch (error) {
      setCartError(errorMessage(error));
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const save = useCallback(async (lines: Array<{ product: Product; quantity: number }>) => {
    const items: CartLineInput[] = lines.map((line) => ({ product_id: line.product.id, quantity: line.quantity }));
    const { data } = await api.post<CartResponse>("/api/cart", {
      items,
    });
    setCart(data);
    setCartError("");
    return data;
  }, []);

  const add = useCallback(async (product: Product, quantity = 1) => {
    const current = cart.items.map((line) => ({
      product: line.product,
      quantity: line.quantity + (line.product.id === product.id ? quantity : 0),
    }));
    if (!current.some((line) => line.product.id === product.id)) current.push({ product, quantity });
    await save(current);
  }, [cart.items, save]);

  const setQuantity = useCallback(async (itemId: number, quantity: number) => {
    try {
      const { data } = await api.patch<CartResponse>(`/api/cart/items/${itemId}`, { quantity });
      setCart(data);
      setCartError("");
    } catch (error) {
      setCartError(errorMessage(error));
    }
  }, []);

  const remove = useCallback(async (itemId: number) => {
    try {
      const { data } = await api.delete<CartResponse>(`/api/cart/items/${itemId}`);
      setCart(data);
      setCartError("");
    } catch (error) {
      setCartError(errorMessage(error));
    }
  }, []);

  const value = useMemo(() => ({
    cart, cartError, refresh, add, save, setQuantity, remove,
    count: cart.items.reduce((sum, line) => sum + line.quantity, 0),
  }), [cart, cartError, refresh, add, save, setQuantity, remove]);
  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}
