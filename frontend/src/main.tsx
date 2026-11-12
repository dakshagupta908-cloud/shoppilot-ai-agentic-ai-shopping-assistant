import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import "./pages.css";
import "./mobile.css";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("Missing root element.");

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode><App /></React.StrictMode>,
);
