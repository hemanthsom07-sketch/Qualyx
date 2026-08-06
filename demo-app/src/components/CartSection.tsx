import { PRODUCTS } from "../products";
import type { CartState } from "../cart";
import { cartSubtotal } from "../cart";

interface CartSectionProps {
  cart: CartState;
  onCheckout: () => void;
  orderConfirmed: boolean;
}

function CartSection({ cart, onCheckout, orderConfirmed }: CartSectionProps) {
  const items = Object.entries(cart).filter(([, qty]) => qty > 0);
  const subtotal = cartSubtotal(cart, PRODUCTS);

  return (
    <section
      id="cart-section"
      data-testid="cart-section"
      className="border border-slate-200 rounded-lg p-4 flex flex-col gap-3"
    >
      <h2 className="font-medium">Cart</h2>

      {items.length === 0 ? (
        <p data-testid="cart-empty-state" className="text-slate-500 text-sm">
          Your cart is empty.
        </p>
      ) : (
        <ul className="flex flex-col gap-1 text-sm">
          {items.map(([productId, qty]) => {
            const product = PRODUCTS.find((p) => p.id === productId);
            if (!product) return null;
            return (
              <li key={productId} data-testid={`cart-item-${productId}`}>
                {product.name} x{qty} — ${(product.price * qty).toFixed(2)}
              </li>
            );
          })}
        </ul>
      )}

      <p data-testid="cart-subtotal" className="font-medium">
        Subtotal: ${subtotal.toFixed(2)}
      </p>

      <button
        id="checkout-button"
        data-testid="checkout-button"
        onClick={onCheckout}
        disabled={items.length === 0}
        className="bg-emerald-600 disabled:bg-slate-300 text-white rounded-md py-2 text-sm hover:bg-emerald-500"
      >
        Checkout
      </button>

      {orderConfirmed && (
        <p data-testid="checkout-confirmation" className="text-emerald-600 text-sm">
          Thank you! Your demo order was placed.
        </p>
      )}
    </section>
  );
}

export default CartSection;
