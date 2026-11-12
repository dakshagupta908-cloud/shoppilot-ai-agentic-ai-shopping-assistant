import { ArrowLeft, ArrowRight, Check, Minus, Scale } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage } from "../services/api";
import type { Product } from "../types";

const money = (value: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);

export default function Compare() {
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let stored: unknown;
    try {
      stored = JSON.parse(localStorage.getItem("shoppilot-compare") || "[]");
    } catch {
      localStorage.removeItem("shoppilot-compare");
      setLoading(false);
      return;
    }
    const ids = Array.isArray(stored)
      ? stored.filter((item): item is { id: string } => item && typeof item.id === "string").map((item) => item.id).slice(0, 3)
      : [];
    if (ids.length < 2) { setLoading(false); return; }
    api.post<{ products: Product[] }>("/api/agent/compare", { product_ids: ids })
      .then(({ data }) => setProducts(data.products))
      .catch((requestError: unknown) => setError(errorMessage(requestError)))
      .finally(() => setLoading(false));
  }, []);
  const remove = (id: string) => {
    const next = products.filter((p) => p.id !== id);
    setProducts(next);
    localStorage.setItem("shoppilot-compare", JSON.stringify(next));
  };
  const specKeys = [...new Set(products.flatMap((p) => Object.keys(p.specifications || {})))];
  if (loading) return <main className="page-shell shell"><div className="loading-panel" role="status">Loading comparison…</div></main>;
  if (!products.length) return <main className="page-shell shell">{error && <div className="error-panel" role="alert">{error}</div>}<div className="empty-state"><div className="empty-icon"><Scale size={23} /></div><h2>Choose products to compare</h2><p>Select two or three products from the catalogue to see their specs side by side.</p><Link className="button button-dark" to="/products">Browse products <ArrowRight size={16} /></Link></div></main>;
  return <main className="page-shell shell">
    <Link className="back-link" to="/products"><ArrowLeft size={15} /> Back to products</Link>
    <div className="page-heading compare-heading"><div><p className="eyebrow">SIDE BY SIDE</p><h1>Compare your shortlist</h1><p>Differences shown directly from catalogue specifications.</p></div><span className="compare-count">{products.length} products</span></div>
    {error && <div className="error-panel">{error}</div>}
    <div className="comparison-scroll"><table className="comparison-table"><thead><tr><th>At a glance</th>{products.map((p) => <th key={p.id}><div className="compare-product"><img src={p.image_url} alt={p.name} /><div><small>{p.brand}</small><strong>{p.name}</strong><span>{money(p.price)}</span></div><button onClick={() => remove(p.id)} className="remove-compare" aria-label={`Remove ${p.name}`}><Minus size={14} /></button></div></th>)}</tr></thead><tbody>
      <tr><th>Category</th>{products.map((p) => <td key={p.id}>{p.category}</td>)}</tr>
      <tr><th>Rating <small>Demo data</small></th>{products.map((p) => <td key={p.id}>★ {Number(p.rating).toFixed(1)} <small className="demo-tag">sample</small></td>)}</tr>
      <tr><th>Availability</th>{products.map((p) => <td key={p.id}><span className="stock-tag"><Check size={13} /> {p.in_stock ? "In stock" : "Out of stock"}</span></td>)}</tr>
      {specKeys.map((key) => <tr key={key}><th>{key}</th>{products.map((p) => <td key={p.id}>{p.specifications[key] || <span className="not-listed">Not listed</span>}</td>)}</tr>)}
      <tr><th>Details</th>{products.map((p) => <td key={p.id}><Link className="text-link" to={`/products/${p.id}`}>View details <ArrowRight size={14} /></Link></td>)}</tr>
    </tbody></table></div>
    <div className="compare-summary"><div className="summary-icon"><Scale size={19} /></div><div><p className="eyebrow">A THOUGHTFUL NEXT STEP</p><strong>Compare what matters to you.</strong><p>Specifications vary by product. The right fit depends on your needs, budget and preferences—there isn’t a one-size-fits-all winner.</p></div><Link to="/assistant" className="button button-dark">Ask the AI agent <ArrowRight size={15} /></Link></div>
  </main>;
}
