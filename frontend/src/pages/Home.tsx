import { ArrowDownRight, ArrowRight, BadgeCheck, Bot, ChevronRight, Command, Layers3, Search, ShieldCheck, Sparkles, WandSparkles } from "lucide-react";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import ProductCard from "../components/ProductCard";
import { useCart } from "../context/useCart";
import { api, errorMessage } from "../services/api";
import type { Product, ProductListResponse } from "../types";

const categoryIcons: Record<string, string> = { Laptops: "⌘", Smartphones: "◉", Headphones: "◖", Keyboards: "⌨", Monitors: "▣", Accessories: "✳" };

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [heroProduct, setHeroProduct] = useState<Product | null>(null);
  const [catalogueCount, setCatalogueCount] = useState(0);
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { add } = useCart();
  useEffect(() => {
    api.get<ProductListResponse>("/api/products", { params: { sort: "rating" } }).then(({ data }) => {
      setProducts(data.products.slice(0, 4));
      setCategories(data.categories);
      setHeroProduct(data.products[0] || null);
      setCatalogueCount(data.products.length);
    }).catch((e: unknown) => setError(errorMessage(e))).finally(() => setLoading(false));
  }, []);
  const start = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    navigate("/assistant", { state: { prompt } });
  };
  return <main>
    <section className="hero shell">
      <div className="hero-copy">
        <div className="pill"><span className="pulse-dot" /> YOUR PERSONAL SHOPPING AGENT <span className="pill-new">AI</span></div>
        <h1>Shopping, with<br />a little more <em>intelligence.</em></h1>
        <p>Tell us what you need. ShopPilot finds the options that fit your life, not just your search terms.</p>
        <form className="hero-search" onSubmit={start}>
          <Sparkles size={20} />
          <input value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="e.g. A light laptop for coding under ₹60,000" aria-label="Describe what you are shopping for" />
          <button type="submit" aria-label="Start shopping"><ArrowRight size={19} /></button>
        </form>
        <div className="hero-hints"><span>Try:</span>{["Laptop under ₹60k", "Headphones for travel", "Phone with a great camera"].map((item) => <button key={item} onClick={() => { setPrompt(item); navigate("/assistant", { state: { prompt: item } }); }}>{item}</button>)}</div>
        <div className="hero-proof"><span className="avatar-stack"><b>R</b><b>A</b><b>M</b></span><span>Thoughtful picks, backed by real catalogue data</span><BadgeCheck size={16} /></div>
      </div>
      <div className="hero-art">
        <div className="art-glow" />
        <div className="orbit orbit-one" /><div className="orbit orbit-two" />
        <div className="art-card main-art-card">
          <div className="art-card-top"><span className="art-icon"><Bot size={19} /></span><span className="live-label"><i /> CATALOGUE-POWERED</span></div>
          <p className="art-caption">YOUR REQUEST</p>
          <div className="request-box">“A good laptop for coding, under ₹60k”</div>
          <div className="agent-thinking"><span className="thinking-mark"><WandSparkles size={16} /></span><div><strong>Search products that fit your needs</strong><small>Searching {catalogueCount || "the"} products in the catalogue</small></div><div className="thinking-bars"><i /><i /><i /></div></div>
          {heroProduct && <div className="mini-product"><div className="mini-image"><img src={heroProduct.image_url} alt="" /></div><div><small>CATALOGUE PICK · DEMO RATING</small><strong>{heroProduct.name}</strong><span>{Object.values(heroProduct.specifications || {}).slice(0, 2).join(" · ")}</span></div><b>{new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(heroProduct.price)}</b></div>}
        </div>
        <div className="floating-note note-top"><span>✦</span> Picks from your real catalogue</div>
        <div className="floating-note note-bottom"><div className="check-bubble"><CheckIcon /></div><span><b>Your call, always.</b><small>No purchase without approval</small></span></div>
        <div className="art-sparkle spark-one">✳</div><div className="art-sparkle spark-two">✦</div>
      </div>
      <div className="hero-scroll"><ArrowDownRight size={14} /> SCROLL TO EXPLORE</div>
    </section>

    <section className="category-section section shell">
      <div className="section-heading"><div><p className="eyebrow">A BETTER WAY TO FIND YOUR NEXT THING</p><h2>What are you shopping for?</h2></div><Link className="text-link" to="/products">Browse everything <ArrowRight size={16} /></Link></div>
      {loading ? <div className="loading-panel" role="status">Loading categories…</div> : <div className="category-grid">{categories.map((name, index) => <Link className={`category-tile tone-${index}`} to={`/products?category=${encodeURIComponent(name)}`} key={name}><span className="category-icon">{categoryIcons[name] || "✳"}</span><strong>{name}</strong><span>Explore picks <ChevronRight size={14} /></span></Link>)}</div>}
    </section>

    <section className="featured section">
      <div className="shell">
        <div className="section-heading"><div><p className="eyebrow">CURATED FOR YOU</p><h2>Good picks, no guesswork.</h2><p className="section-sub">A few standouts from our catalogue, selected for their thoughtful balance of features and value.</p></div><Link className="text-link" to="/products">Explore products <ArrowRight size={16} /></Link></div>
        {error && <div className="inline-error">{error}</div>}
        {loading ? <div className="loading-panel" role="status">Loading featured products…</div> : <div className="product-grid">{products.map((product) => <ProductCard key={product.id} product={product} onAdd={add} />)}</div>}
      </div>
    </section>

    <section className="how-section section shell">
      <div className="how-intro"><p className="eyebrow">LESS SCROLLING. MORE CONFIDENCE.</p><h2>From “I need…”<br />to “that’s the one.”</h2><p>No endless tabs. Just a little conversation and a much clearer choice.</p><Link className="button button-dark" to="/assistant">Meet your shopping agent <ArrowRight size={16} /></Link></div>
      <div className="steps">{([
        { icon: <Search size={20} />, number: "01", title: "Tell us what matters", copy: "Budget, must-haves, nice-to-haves. Talk like a person." },
        { icon: <Layers3 size={20} />, number: "02", title: "Get considered matches", copy: "We search real products, then explain the trade-offs." },
        { icon: <ShieldCheck size={20} />, number: "03", title: "You choose what’s next", copy: "Compare, add to cart, and approve checkout yourself." },
      ] satisfies Array<{ icon: ReactNode; number: string; title: string; copy: string }>).map(({ icon, number, title, copy }) => <div className="step-card" key={number}><div className="step-icon">{icon}<span>{number}</span></div><h3>{title}</h3><p>{copy}</p></div>)}</div>
    </section>
    <section className="closing shell"><div className="closing-icon"><Command size={21} /></div><div><p className="eyebrow">SHOP SMARTER, NOT HARDER</p><h2>Your next great find starts with a sentence.</h2></div><Link to="/assistant" className="button button-light">Start a conversation <ArrowRight size={16} /></Link></section>
  </main>;
}

function CheckIcon() {
  return <svg viewBox="0 0 16 16" width="15" height="15" fill="none" aria-hidden="true"><path d="m3.3 8.3 3.1 3.1 6.4-6.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
