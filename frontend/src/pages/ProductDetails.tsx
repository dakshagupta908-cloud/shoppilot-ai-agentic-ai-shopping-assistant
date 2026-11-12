import { ArrowLeft, ArrowRight, Check, ShoppingBag, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useCart } from "../context/useCart";
import { api, errorMessage } from "../services/api";
import type { Product } from "../types";

export default function ProductDetails() {
  const { productId } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(null);
  const [error, setError] = useState("");
  const [added, setAdded] = useState(false);
  const [actionError, setActionError] = useState("");
  const { add } = useCart();
  useEffect(() => {
    let active = true;
    setProduct(null);
    setError("");
    api.get<Product>(`/api/products/${productId}`)
      .then(({ data }) => { if (active) setProduct(data); })
      .catch((requestError: unknown) => { if (active) setError(errorMessage(requestError)); });
    return () => { active = false; };
  }, [productId]);
  if (error) return <main className="page-shell shell"><div className="error-panel">{error}</div><Link className="back-link" to="/products"><ArrowLeft size={15} /> Back to products</Link></main>;
  if (!product) return <main className="page-shell shell"><div className="loading-panel">Loading product details…</div></main>;
  const money = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(product.price);
  return <main className="page-shell shell">
    <Link className="back-link" to="/products"><ArrowLeft size={15} /> All products</Link>
    <div className="detail-layout"><div className="detail-image"><img src={product.image_url} alt={product.name} /><span className="product-category">{product.category}</span></div>
      <div className="detail-copy"><p className="eyebrow">{product.brand} · {product.category.toUpperCase()}</p><h1>{product.name}</h1><div className="detail-rating">★ {Number(product.rating).toFixed(1)} <small>Illustrative demo rating</small></div><p className="detail-description">{product.description}</p><div className="detail-price">{money}<small>INR · inclusive of listed price</small></div><div className="stock-status"><Check size={15} /> {product.in_stock ? "In stock and ready to ship" : "Currently unavailable"}</div><div className="detail-actions"><button className="button button-dark" disabled={!product.in_stock} onClick={async () => { try { await add(product); setAdded(true); setActionError(""); } catch (requestError) { setActionError(errorMessage(requestError)); } }}>{added ? <Check size={17} /> : <ShoppingBag size={17} />}{added ? "Added to cart" : "Add to cart"}</button><button className="button button-outline" onClick={() => navigate("/assistant", { state: { prompt: `Tell me about ${product.name} and how it compares to alternatives.` } })}><Sparkles size={16} /> Ask AI about this</button></div>
        {actionError && <div className="inline-error" role="alert">{actionError}</div>}
        <div className="detail-specs"><h2>Product specifications</h2>{Object.entries(product.specifications).map(([key, value]) => <div className="spec-row" key={key}><span>{key}</span><strong>{value}</strong></div>)}</div>
        <Link className="text-link detail-compare" to="/products">Looking at a few options? Compare in catalogue <ArrowRight size={15} /></Link>
      </div>
    </div>
  </main>;
}
