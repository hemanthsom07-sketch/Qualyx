// Qualyx Demo Store — static product catalog.
// Deliberately local/static: no backend, no database. Data is fixed so
// that recorded journeys and generated tests stay deterministic.

export interface Product {
  id: string;
  name: string;
  price: number;
}

export const PRODUCTS: Product[] = [
  { id: "prod-1", name: "Wireless Mouse", price: 24.99 },
  { id: "prod-2", name: "Mechanical Keyboard", price: 79.99 },
  { id: "prod-3", name: "USB-C Hub", price: 34.5 }
];
