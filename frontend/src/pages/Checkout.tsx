import { AlertCircle, ArrowLeft, ArrowRight, LoaderCircle, LockKeyhole, ShieldCheck } from "lucide-react";
import { PayPalButtons, PayPalScriptProvider } from "@paypal/react-paypal-js";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCart } from "../context/useCart";
import { api, errorMessage } from "../services/api";
import type { CartLineInput, CheckoutQuote, CreatedPayPalOrder, HealthResponse, Order } from "../types";

const clientId = import.meta.env.VITE_PAYPAL_CLIENT_ID || "";
const money = (value: string | number, currency = "INR") => new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: currency === "USD" ? 2 : 0 }).format(Number(value || 0));

export default function Checkout() {
  const { cart, refresh } = useCart();
  const [quote, setQuote] = useState<CheckoutQuote | null>(null);
  const [quoteError, setQuoteError] = useState("");
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [paypalConfigured, setPaypalConfigured] = useState(false);
  const [error, setError] = useState("");
  const [processing, setProcessing] = useState(false);
  const [quoteAttempt, setQuoteAttempt] = useState(0);
  const navigate = useNavigate();
  const paypalOrderId = useRef<string | null>(null);
  const lines: CartLineInput[] = cart.items.map((line) => ({ product_id: line.product.id, quantity: line.quantity }));
  const lineSignature = JSON.stringify(lines);
  useEffect(() => {
    if (!lineSignature || lineSignature === "[]") return;
    setQuote(null);
    setQuoteError("");
    setQuoteLoading(true);
    setPaypalConfigured(false);
    setError("");
    const controller = new AbortController();
    const checkoutItems = JSON.parse(lineSignature);
    Promise.all([
      api.post<CheckoutQuote>("/api/paypal/quote", { items: checkoutItems }, { signal: controller.signal }),
      api.get<HealthResponse>("/api/health", { signal: controller.signal }),
    ])
      .then(([quoteResponse, healthResponse]) => {
        if (controller.signal.aborted) return;
        setQuote(quoteResponse.data);
        setPaypalConfigured(Boolean(healthResponse.data.paypal_configured && clientId));
      })
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) setQuoteError(errorMessage(requestError));
      })
      .finally(() => {
        if (!controller.signal.aborted) setQuoteLoading(false);
      });
    return () => controller.abort();
  }, [lineSignature, quoteAttempt]);

  if (!cart.items.length) return <main className="page-shell shell"><div className="empty-state"><h2>Nothing to check out yet</h2><p>Add something to your cart first.</p><Link className="button button-dark" to="/products">Browse products <ArrowRight size={16} /></Link></div></main>;
  const paymentButtons = <PayPalButtons
    style={{ layout: "vertical", shape: "rect", label: "paypal", color: "gold" }}
    createOrder={async () => {
      setError("");
      const { data } = await api.post<CreatedPayPalOrder>("/api/paypal/create-order", { items: lines });
      paypalOrderId.current = data.id || null;
      if (!data.id || data.currency !== "USD" || !quote || data.amount !== quote.amount) throw new Error("PayPal order did not match the displayed server quote. Please refresh checkout.");
      return data.id;
    }}
    onApprove={async (data) => {
      setProcessing(true); setError("");
      try {
        const { data: order } = await api.post<Order>("/api/paypal/capture-order", { order_id: data.orderID });
        if (order.status === "COMPLETED" && order.paypal_capture_id) {
          await refresh();
          navigate(`/order-success/${order.id}`);
        } else if (order.status === "PENDING" || order.status === "FAILED") {
          navigate(`/order-success/${order.id}`);
        } else {
          throw new Error("PayPal has not confirmed the payment. The order will not be shown as paid.");
        }
      } catch (e) { setError(errorMessage(e)); }
      finally { setProcessing(false); }
    }}
    onCancel={async (data) => {
      const orderId = typeof data.orderID === "string" ? data.orderID : paypalOrderId.current;
      if (orderId) {
        try {
          await api.post<Order>("/api/paypal/cancel-order", { order_id: orderId });
          paypalOrderId.current = null;
          setError("Checkout was cancelled. No payment was captured.");
        } catch (cancelError) {
          setError(`Checkout was cancelled, but the order status could not be updated: ${errorMessage(cancelError)}`);
        }
      } else {
        setError("Checkout was cancelled. No payment was captured.");
      }
    }}
    onError={(providerError) => setError(errorMessage(providerError))}
  />;
  return <main className="page-shell shell checkout-page">
    <Link className="back-link" to="/cart"><ArrowLeft size={15} /> Return to cart</Link>
    <div className="page-heading"><div><p className="eyebrow">ONE LAST LOOK</p><h1>Review &amp; checkout</h1><p>Your purchase only happens after you approve it with PayPal.</p></div><div className="sandbox-badge"><span /> PAYPAL SANDBOX</div></div>
    <div className="checkout-layout"><section className="checkout-main"><div className="checkout-section-title"><div><span className="checkout-step">01</span><div><h2>Your order</h2><p>Double-check your picks before payment.</p></div></div><Link to="/cart">Edit cart</Link></div>
      <div className="checkout-lines">{cart.items.map((line) => <div className="checkout-line" key={line.item_id}><img src={line.product.image_url} alt="" /><div><strong>{line.product.name}</strong><small>Qty {line.quantity} · {money(line.product.price)} each</small></div><b>{money(line.line_total)}</b></div>)}</div>
      <div className="checkout-section-title payment-title"><div><span className="checkout-step">02</span><div><h2>Secure payment</h2><p>PayPal Sandbox checkout. Your approval is required.</p></div></div><LockKeyhole size={18} /></div>
      {!clientId && <div className="config-notice"><AlertCircle size={19} /><div><strong>PayPal Sandbox needs setup</strong><p>Add your public Sandbox client ID to <code>frontend/.env</code> and configure the matching client ID and secret in <code>backend/.env</code>. No payment will be simulated.</p></div></div>}
      {clientId && !paypalConfigured && quote && <div className="config-notice"><AlertCircle size={19} /><div><strong>PayPal isn’t ready yet</strong><p>Set Sandbox client credentials in <code>backend/.env</code> and confirm the client ID in <code>frontend/.env</code>. Checkout remains disabled until configured.</p></div></div>}
      {paypalConfigured && quote && <PayPalScriptProvider options={{ clientId, currency: "USD", intent: "capture" }}>{paymentButtons}</PayPalScriptProvider>}
      {processing && <div className="processing-note"><LoaderCircle className="spin" size={17} /> Verifying your payment with PayPal…</div>}
      {error && <div className="payment-error" role="alert"><AlertCircle size={16} /> {error} {paypalOrderId.current && <Link to="/orders">Check order history</Link>}</div>}
      <div className="approval-note"><ShieldCheck size={18} /><span><b>You’re in control.</b> ShopPilot never places an order or captures a payment without your explicit PayPal approval.</span></div>
    </section>
    <aside className="order-summary checkout-summary"><p className="eyebrow">PAYMENT SUMMARY</p><div className="summary-row"><span>Subtotal (INR)</span><strong>{money(cart.subtotal)}</strong></div><div className="summary-row"><span>Shipping</span><strong>Free</strong></div><div className="summary-divider" />
      {quote ? <><div className="summary-row summary-total"><span>Total in USD</span><strong>{money(quote.amount, "USD")}</strong></div><div className="conversion-box"><span>Converted from {money(quote.source_amount)}</span><strong>Rate: ₹1 = ${Number(quote.conversion_rate).toFixed(4)} USD</strong><small>Demo conversion rate disclosed for this Sandbox transaction.</small></div></> : quoteLoading ? <div className="processing-note"><LoaderCircle className="spin" size={16} /> Calculating checkout total…</div> : quoteError ? <div className="payment-error" role="alert">{quoteError}<button className="dock-clear" onClick={() => setQuoteAttempt((attempt) => attempt + 1)}>Retry quote</button></div> : null}
      <div className="summary-divider" /><div className="sandbox-note"><span className="sandbox-dot" /> Sandbox environment · No real funds are charged</div>
    </aside></div>
  </main>;
}
