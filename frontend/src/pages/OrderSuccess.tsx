import { ArrowRight, Check, PackageCheck, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorMessage } from "../services/api";
import type { Order } from "../types";

export default function OrderSuccess() {
  const { orderId } = useParams();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!orderId) return;
    let active = true;
    setOrder(null);
    setError("");
    api.get<Order>(`/api/orders/${orderId}`)
      .then(({ data }) => { if (active) setOrder(data); })
      .catch((requestError: unknown) => { if (active) setError(errorMessage(requestError)); });
    return () => { active = false; };
  }, [orderId]);
  if (error) return <main className="page-shell shell"><div className="error-panel">{error}</div><Link className="button button-dark" to="/orders">View order history</Link></main>;
  if (!order) return <main className="page-shell shell"><div className="loading-panel">Retrieving verified order…</div></main>;
  const verified = order.status === "COMPLETED" && Boolean(order.paypal_capture_id);
  const statusHeading: Record<Order["status"], string> = {
    CREATED: "Checkout not completed.",
    CAPTURING: "Payment verification is underway.",
    PENDING: "Payment is still processing.",
    COMPLETED: "That’s a great choice.",
    FAILED: "Payment could not be verified.",
    CANCELLED: "Checkout was cancelled.",
  };
  const statusCopy: Record<Order["status"], string> = {
    CREATED: "This order has not been captured. Return to checkout to try again.",
    CAPTURING: "PayPal is processing the capture. Check order history again shortly.",
    PENDING: "We can’t show this order as paid until PayPal confirms the capture. Check order history later or contact support if it remains pending.",
    COMPLETED: "PayPal confirmed your payment. Your order details are below.",
    FAILED: "PayPal did not verify this as a successful order. It may have been declined or failed validation, and ShopPilot will not mark it as paid.",
    CANCELLED: "No payment was captured for this cancelled checkout.",
  };
  return <main className="page-shell shell success-page"><div className={`success-mark ${verified ? "" : "pending"}`}>{verified ? <Check size={31} /> : <PackageCheck size={31} />}</div><p className="eyebrow">{verified ? "PAYMENT VERIFIED" : "ORDER STATUS"}</p><h1>{statusHeading[order.status]}</h1><p className="success-copy">{statusCopy[order.status]}</p>
    <div className="success-receipt"><div className="receipt-head"><div><small>ORDER REFERENCE</small><strong>{order.id}</strong></div><span className={`status-pill ${verified ? "status-paid" : ""}`}>{order.status}</span></div>
      {order.items.map((item) => <div className="receipt-line" key={item.product_id}><div><strong>{item.name}</strong><small>Quantity {item.quantity}</small></div><span>{item.quantity} × {new Intl.NumberFormat("en-US", { style: "currency", currency: order.currency }).format(item.unit_price)}</span></div>)}
      <div className="receipt-total"><span>{verified ? "Total paid" : "Order total"}</span><strong>{new Intl.NumberFormat("en-US", { style: "currency", currency: order.currency }).format(order.amount)}</strong></div>
      <div className="receipt-capture"><ShieldCheck size={16} /><span>PayPal capture reference</span><code>{order.paypal_capture_id || "Not captured"}</code></div>
    </div>
    <div className="success-actions"><Link className="button button-dark" to="/orders">View order history <ArrowRight size={16} /></Link><Link className="text-link" to="/products">Continue exploring</Link></div>
  </main>;
}
