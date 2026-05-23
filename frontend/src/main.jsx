/**
 * main.jsx — Entry point.
 * BrowserRouter aquí, no dentro de App.jsx, para que
 * useNavigate/useLocation funcionen en todos los componentes.
 */
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";
 
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
