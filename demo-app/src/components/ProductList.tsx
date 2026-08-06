import { PRODUCTS } from "../products";
import ProductCard from "./ProductCard";

interface ProductListProps {
  onAddToCart: (productId: string) => void;
}

function ProductList({ onAddToCart }: ProductListProps) {
  return (
    <section data-testid="product-list" className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {PRODUCTS.map((product) => (
        <ProductCard key={product.id} product={product} onAddToCart={onAddToCart} />
      ))}
    </section>
  );
}

export default ProductList;
