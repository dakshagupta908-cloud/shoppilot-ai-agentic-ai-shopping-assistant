import { useState } from "react";
import { ArrowUpRight, Check, Plus, Scale } from "lucide-react";
import { Link } from "react-router-dom";
import { errorMessage } from "../services/api";
import type { Product } from "../types";

type ProductCardProps = {
  product: Product;
  onAdd: (product: Product) => void | Promise<void>;
  selected?: boolean;
  onCompare?: (product: Product) => void;
  compact?: boolean;
};

export default function ProductCard({ product, onAdd, selected = false, onCompare, compact = false }: ProductCardProps) {
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState("");

  const addProduct = async () => {
    setAdding(true);
    setAddError("");
    try {
      await onAdd(product);
    } catch (error) {
      setAddError(errorMessage(error));
    } finally {
      setAdding(false);
    }
  };

  return (
    <article className={`product-card ${compact ? "product-card-compact" : ""}`}>
      <Link to={`/products/${product.id}`} className="product-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        <span className="product-category">{product.category}</span>
      </Link>
      <div className="product-card-body">
        <div className="product-title-row">
          <div><p className="eyebrow">{product.brand}</p><Link to={`/products/${product.id}`} className="product-title">{product.name}</Link></div>
          <span className="rating">★ {Number(product.rating).toFixed(1)}</span>
        </div>
        <p className="product-description">{product.description}</p>
        <div className="spec-chips">{Object.entries(product.specifications || {}).slice(0, 2).map(([key, value]) => <span key={key}>{value}</span>)}</div>
        <div className="product-card-footer">
          <div><strong>{new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(product.price)}</strong><small>Demo rating</small></div>
          <div className="card-actions">
            {onCompare && <button className={`icon-button ${selected ? "selected" : ""}`} onClick={() => onCompare(product)} aria-label="Compare product" title="Compare"><Scale size={17} /></button>}
            <button className="add-button" disabled={adding} onClick={() => void addProduct()} title="Add to cart">{adding ? <span className="button-spinner" /> : selected ? <Check size={17} /> : <Plus size={17} />}<span>{adding ? "Adding" : selected ? "Added" : "Add"}</span><ArrowUpRight size={14} /></button>
          </div>
        </div>
        {addError && <p className="inline-error product-add-error" role="alert">{addError}</p>}
      </div>
    </article>
  );
}
