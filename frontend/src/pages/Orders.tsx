import { ArrowRight, Clock3, PackageCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../services/api";
import type { Order, OrdersResponse } from "../types";

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.get<OrdersResponse>("/api/orders")
      .then(({ data }) => setOrders(data.orders))
      .catch((requestError: unknown) => setError(errorMessage(requestError)))
      .finally(() => setLoading(false));
  }, []);
  const money = (value: number, currency: string) => new Intl.NumberFormat("en-US", { style: "currency", currency }).format(value);
  return <main className="page-shell shell">
    <div className="page-heading"><div><p className="eyebrow">YOUR SHOPPING HISTORY</p><h1>Orders</h1><p>Orders placed from this browser session.</p></div><span className="compare-count">{orders.length} {orders.length === 1 ? "order" : "orders"}</span></div>
    {error && <div className="error-panel">{error}</div>}
    {loading ? <div className="loading-panel" role="status">Loading your guest-session orders…</div> : orders.length ? <div className="orders-list">{orders.map((order) => <Link className="order-card" to={`/order-success/${order.id}`} key={order.id}><div className="order-card-icon">{order.status === "COMPLETED" ? <PackageCheck size={20} /> : <Clock3 size={20} />}</div><div className="order-card-main"><small>ORDER {order.id.slice(0, 8).toUpperCase()} · {new Date(order.created_at).toLocaleDateString()}</small><strong>{order.items.map((i) => i.name).join(", ")}</strong><span>{order.items.reduce((sum, item) => sum + item.quantity, 0)} items · PayPal Sandbox</span></div><div className="order-card-end"><b>{money(order.amount, order.currency)}</b><span className={`status-pill ${order.status === "COMPLETED" ? "status-paid" : ""}`}>{order.status}</span></div><ArrowRight size={16} /></Link>)}</div> :
    <div className="empty-state"><div className="empty-icon"><PackageCheck size={23} /></div><h2>Your next great find awaits</h2><p>Verified purchases will show up here after checkout.</p><Link className="button button-dark" to="/assistant">Find something with AI <ArrowRight size={16} /></Link></div>}
    <div className="guest-disclaimer">Order history is scoped to this browser’s guest session; it is not an authenticated account.</div>
  </main>;
}
