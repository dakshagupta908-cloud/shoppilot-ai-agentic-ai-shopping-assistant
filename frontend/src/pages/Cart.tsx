import { ArrowLeft, ArrowRight, Minus, Plus, ShoppingBag, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { useCart } from "../context/useCart";

const money = (value: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value || 0);

export default function Cart() {
  const { cart, cartError, setQuantity, remove } = useCart();
  return <main className="page-shell shell">
    <div className="page-heading"><div><p className="eyebrow">YOUR SHORTLIST</p><h1>Shopping cart</h1><p>Everything you’ve chosen, ready when you are.</p></div><span className="compare-count">{cart.items.length} {cart.items.length === 1 ? "item" : "items"}</span></div>
    {cartError && <div className="error-panel">{cartError}</div>}
    {!cart.items.length ? <div className="empty-state"><div className="empty-icon"><ShoppingBag size={24} /></div><h2>Your cart is taking a breather</h2><p>Find something that fits and add it here when you’re ready.</p><Link className="button button-dark" to="/products">Explore products <ArrowRight size={16} /></Link></div> :
      <div className="cart-layout"><div className="cart-lines">{cart.items.map((line) => <article className="cart-line" key={line.item_id}>
        <Link to={`/products/${line.product.id}`} className="cart-image"><img src={line.product.image_url} alt={line.product.name} /></Link>
        <div className="cart-info"><small>{line.product.brand} · {line.product.category}</small><Link to={`/products/${line.product.id}`}><strong>{line.product.name}</strong></Link><span>{money(line.product.price)} each</span>
          <div className="quantity-control"><button aria-label="Decrease quantity" disabled={line.quantity <= 1} onClick={() => setQuantity(line.item_id, line.quantity - 1)}><Minus size={14} /></button><span>{line.quantity}</span><button aria-label="Increase quantity" onClick={() => setQuantity(line.item_id, line.quantity + 1)}><Plus size={14} /></button></div>
        </div><div className="cart-line-end"><strong>{money(line.line_total)}</strong><button className="remove-item" onClick={() => remove(line.item_id)}><Trash2 size={15} /> Remove</button></div>
      </article>)}
      <Link to="/products" className="back-link cart-continue"><ArrowLeft size={15} /> Continue shopping</Link></div>
      <aside className="order-summary"><p className="eyebrow">ORDER SUMMARY</p><div className="summary-row"><span>Subtotal</span><strong>{money(cart.subtotal)}</strong></div><div className="summary-row"><span>Shipping</span><strong>Free</strong></div><div className="summary-divider" /><div className="summary-row summary-total"><span>Total</span><strong>{money(cart.total)}</strong></div><small className="summary-currency">PayPal checkout converts this INR subtotal to USD at a clearly disclosed rate.</small><Link to="/checkout" className="button button-dark checkout-link">Continue to checkout <ArrowRight size={16} /></Link><div className="secure-note">◈ &nbsp; Secure payment · Your approval is always required</div></aside></div>}
  </main>;
}
