import { Bot, ShoppingBag, Sparkles } from "lucide-react";
import { Link, NavLink } from "react-router-dom";
import { useCart } from "../context/useCart";

const links = [
  { label: "Shop", path: "/products" },
  { label: "AI assistant", path: "/assistant" },
  { label: "Orders", path: "/orders" },
];

export default function Navbar() {
  const { count } = useCart();
  return (
    <header className="nav-wrap">
      <nav className="nav shell">
        <Link className="brand" to="/" aria-label="ShopPilot AI home">
          <span className="brand-mark"><Bot size={20} /></span>
          <span>shop<span className="brand-light">pilot</span><small>AI</small></span>
        </Link>
        <div className="nav-links">
          {links.map(({ label, path }) => <NavLink key={path} to={path} className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>{label}</NavLink>)}
        </div>
        <div className="nav-actions">
          <Link className="cart-link" to="/cart"><ShoppingBag size={18} /><span>Cart</span>{count > 0 && <b>{count}</b>}</Link>
          <Link className="nav-cta" to="/assistant"><Sparkles size={15} /> Find my match</Link>
        </div>
      </nav>
    </header>
  );
}
