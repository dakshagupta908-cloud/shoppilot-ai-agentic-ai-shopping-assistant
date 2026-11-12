import { Link } from "react-router-dom";

export default function Footer() {
  return <footer className="footer"><div className="shell footer-inner">
    <div><Link className="brand" to="/"><span className="brand-mark">S</span><span>shop<span className="brand-light">pilot</span><small>AI</small></span></Link><p>Tell us what you need. Let AI find it.<br />You decide. PayPal makes it happen.</p></div>
    <div className="footer-links"><Link to="/products">Explore products</Link><Link to="/assistant">Shopping assistant</Link><Link to="/orders">Order history</Link></div>
    <small className="copyright">© 2026 ShopPilot AI · Demo catalogue and ratings</small>
  </div></footer>;
}
