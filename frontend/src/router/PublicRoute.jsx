/**
 * PublicRoute — Redirige a /dashboard si ya hay sesión activa.
 * Evita que un usuario autenticado vea /login o /register.
 */
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
 
const PublicRoute = () => {
  const { isAuthenticated, isBootstrapping } = useAuthStore();
 
  if (isBootstrapping) return null; // El bootstrap lo maneja App.jsx
 
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <Outlet />;
};
 
export default PublicRoute;
