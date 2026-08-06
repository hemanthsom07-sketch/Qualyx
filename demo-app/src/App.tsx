import { useState } from "react";
import ProductList from "./components/ProductList";
import CartSection from "./components/CartSection";
import { addToCart, cartCount, clearCart } from "./cart";
import type { CartState } from "./cart";

// Qualyx Demo E-commerce Application — deterministic storefront foundation.
// Intentionally does not implement registration, login, search, product
// detail pages, real payment, or persistence. Everything is local React
// state so behavior is fully deterministic for recording/testing.
// Still deliberately excluded: authentication, backend integration,
// database, real payment processing.

function App() {
  const [cart, setCart] = useState<CartState>({});
  const [orderConfirmed, setOrderConfirmed] = useState(false);

  function handleAddToCart(productId: string) {
    setOrderConfirmed(false);
    setCart((prev) => addToCart(prev, productId));
  }

  function handleCheckout() {
    setCart(clearCart());
    setOrderConfirmed(true);
  }

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <header className="border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Qualyx Demo Store</h1>
        <div id="cart-indicator" data-testid="cart-indicator" className="text-sm font-medium">
          Cart (<span data-testid="cart-count">{cartCount(cart)}</span>)
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2">
          <ProductList onAddToCart={handleAddToCart} />
        </div>
        <div>
          <CartSection cart={cart} onCheckout={handleCheckout} orderConfirmed={orderConfirmed} />
        </div>
      </main>
    </div>
  );
}

export default App;
