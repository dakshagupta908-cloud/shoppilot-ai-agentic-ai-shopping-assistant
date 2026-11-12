import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Link } from "react-router-dom";
import Footer from "./components/Footer";
import Navbar from "./components/Navbar";
import { CartProvider } from "./context/CartContext";
import Assistant from "./pages/Assistant";
import Cart from "./pages/Cart";
import Checkout from "./pages/Checkout";
import Compare from "./pages/Compare";
import Home from "./pages/Home";
import OrderSuccess from "./pages/OrderSuccess";
import Orders from "./pages/Orders";
import ProductDetails from "./pages/ProductDetails";
import Products from "./pages/Products";

export default function App() {
  return <BrowserRouter><CartProvider><Navbar /><Routes>
    <Route path="/" element={<Home />} />
    <Route path="/products" element={<Products />} />
    <Route path="/products/:productId" element={<ProductDetails />} />
    <Route path="/assistant" element={<Assistant />} />
    <Route path="/compare" element={<Compare />} />
    <Route path="/cart" element={<Cart />} />
    <Route path="/checkout" element={<Checkout />} />
    <Route path="/orders" element={<Orders />} />
    <Route path="/order-success/:orderId" element={<OrderSuccess />} />
    <Route path="*" element={<main className="page-shell shell"><div className="empty-state"><h1>Page not found</h1><Link to="/" className="button button-dark">Go home</Link></div></main>} />
  </Routes><Footer /></CartProvider></BrowserRouter>;
}
