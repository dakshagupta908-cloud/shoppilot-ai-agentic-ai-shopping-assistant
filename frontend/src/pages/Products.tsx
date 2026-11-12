import { Search, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import ProductCard from "../components/ProductCard";
import { useCart } from "../context/useCart";
import { api, errorMessage } from "../services/api";
import type { Product, ProductListResponse } from "../types";

type SortOption = "featured" | "price_asc" | "price_desc" | "rating";

function storedCompareProducts(): Product[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem("shoppilot-compare") || "[]");
    if (Array.isArray(stored)) return stored.filter((item): item is Product => item && typeof item.id === "string").slice(0, 3);
  } catch {
    localStorage.removeItem("shoppilot-compare");
  }
  return [];
}

export default function Products() {
  const [params, setParams] = useSearchParams();
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [search, setSearch] = useState(params.get("search") || "");
  const [category, setCategory] = useState(params.get("category") || "All");
  const [maxPrice, setMaxPrice] = useState("");
  const [sort, setSort] = useState<SortOption>("featured");
  const [selected, setSelected] = useState<Product[]>(storedCompareProducts);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const { add } = useCart();

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const { data } = await api.get<ProductListResponse>("/api/products", {
          params: {
            search: search.trim() || undefined,
            category: category === "All" ? undefined : category,
            max_price: maxPrice ? Number(maxPrice) : undefined,
            sort,
          },
          signal: controller.signal,
        });
        setProducts(data.products);
        setCategories(data.categories);
      } catch (requestError) {
        if (!controller.signal.aborted) setError(errorMessage(requestError));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 180);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [search, category, maxPrice, sort]);

  const toggleCompare = (product: Product) => {
    const next = selected.some((item) => item.id === product.id)
      ? selected.filter((item) => item.id !== product.id)
      : selected.length < 3 ? [...selected, product] : selected;
    setSelected(next);
    localStorage.setItem("shoppilot-compare", JSON.stringify(next));
  };

  const updateCategory = (value: string) => {
    setCategory(value);
    setParams((previous) => {
      if (value === "All") previous.delete("category");
      else previous.set("category", value);
      return previous;
    });
  };

  return <main className="page-shell shell">
    <div className="page-heading"><div><p className="eyebrow">THE CATALOGUE</p><h1>Explore products</h1><p>Real catalogue data, thoughtful details, and no made-up specs.</p></div><div className="catalogue-count"><span>{products.length.toString().padStart(2, "0")}</span> PRODUCTS</div></div>
    <div className="filter-bar">
      <label className="filter-search"><Search size={17} /><input value={search} onChange={(event) => {
        const value = event.target.value;
        setSearch(value);
        setParams((previous) => {
          if (value.trim()) previous.set("search", value);
          else previous.delete("search");
          return previous;
        });
      }} placeholder="Search products or brands" /></label>
      <label className="select-wrap"><SlidersHorizontal size={15} /><select value={category} onChange={(event) => updateCategory(event.target.value)}><option>All</option>{categories.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label className="filter-price">Up to ₹ <input type="number" min="0" placeholder="Any price" value={maxPrice} onChange={(event) => setMaxPrice(event.target.value)} /></label>
      <select className="sort-select" value={sort} onChange={(event) => setSort(event.target.value as SortOption)}><option value="featured">Sort: Featured</option><option value="price_asc">Price: Low to high</option><option value="price_desc">Price: High to low</option><option value="rating">Top rated</option></select>
    </div>
    {error && <div className="error-panel" role="alert">{error}</div>}
    {loading ? <div className="loading-panel block" role="status">Loading products from the catalogue…</div> :
      products.length ? <div className="product-grid">{products.map((product) => <ProductCard key={product.id} product={product} onAdd={add} selected={selected.some((item) => item.id === product.id)} onCompare={toggleCompare} />)}</div> :
        <div className="empty-state"><span>⌕</span><h2>No matches just yet</h2><p>Try a different search or relax your filters.</p><button className="button button-outline" onClick={() => { setSearch(""); updateCategory("All"); setMaxPrice(""); }}>Clear filters</button></div>}
    {selected.length > 0 && <div className="compare-dock"><span>{selected.length} of 3 products selected</span><Link className={`button button-dark ${selected.length < 2 ? "disabled-link" : ""}`} aria-disabled={selected.length < 2} onClick={(event) => { if (selected.length < 2) event.preventDefault(); }} to="/compare">Compare products →</Link><button className="dock-clear" onClick={() => { setSelected([]); localStorage.removeItem("shoppilot-compare"); }}>Clear</button></div>}
  </main>;
}
