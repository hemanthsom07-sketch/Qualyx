import type { Product } from "../products";

interface ProductCardProps {
  product: Product;
  onAddToCart: (productId: string) => void;
}

// Stable data-testid attributes give the Recorder and future generated
// tests deterministic targets independent of layout/copy changes.
function ProductCard({ product, onAddToCart }: ProductCardProps) {
  return (
    <div
      data-testid={`product-card-${product.id}`}
      className="border border-slate-200 rounded-lg p-4 flex flex-col gap-2"
    >
      <h3 data-testid={`product-name-${product.id}`} className="font-medium">
        {product.name}
      </h3>
      <p data-testid={`product-price-${product.id}`} className="text-slate-500">
        ${product.price.toFixed(2)}
      </p>
      <button
        id={`add-to-cart-${product.id}`}
        data-testid={`add-to-cart-${product.id}`}
        onClick={() => onAddToCart(product.id)}
        className="mt-auto bg-slate-900 text-white rounded-md py-2 text-sm hover:bg-slate-700"
      >
        Add to Cart
      </button>
    </div>
  );
}

export default ProductCard;
