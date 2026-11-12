export type Product = {
  id: string;
  name: string;
  brand: string;
  category: string;
  description: string;
  price: number;
  currency: string;
  specifications: Record<string, string>;
  image_url: string;
  rating: number;
  rating_is_demo: boolean;
  stock_quantity: number;
  in_stock: boolean;
};

export type ProductListResponse = {
  products: Product[];
  categories: string[];
};

export type CartLineInput = {
  product_id: string;
  quantity: number;
};

export type CartLine = {
  item_id: number;
  product: Product;
  quantity: number;
  line_total: number;
};

export type CartResponse = {
  session_id: string;
  items: CartLine[];
  subtotal: number;
  total: number;
  currency: string;
};

export type AgentRequirements = {
  category: string | null;
  max_budget: number | null;
  minimum_ram_gb: number | null;
  keywords: string[];
  currency: string;
};

export type Recommendation = {
  product: Product;
  score: number;
  explanation: string;
};

export type AgentResponse = {
  requirements: AgentRequirements;
  recommendations: Recommendation[];
  response: string;
  mode: string;
};

export type CompareResponse = {
  products: Product[];
};

export type CheckoutQuote = {
  amount: string;
  currency: "USD";
  source_amount: string;
  source_currency: "INR";
  conversion_rate: number;
};

export type CreatedPayPalOrder = CheckoutQuote & {
  id: string;
};

export type OrderItem = {
  product_id: string;
  name: string;
  unit_price: number;
  quantity: number;
};

export type Order = {
  id: string;
  paypal_order_id: string;
  paypal_capture_id: string | null;
  status: "CREATED" | "CAPTURING" | "PENDING" | "COMPLETED" | "FAILED" | "CANCELLED";
  amount: number;
  currency: string;
  created_at: string;
  items: OrderItem[];
};

export type OrdersResponse = {
  orders: Order[];
};

export type HealthResponse = {
  status: string;
  service: string;
  paypal_configured: boolean;
};
