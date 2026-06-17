/**
 * PrivateRoute — Redirige a /login si no hay sesión activa.
 * Depende del bootstrap: muestra spinner mientras isBootstrapping=true.
 * Una vez bootstrap completo, evalúa isAuthenticated.
 */
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
 
const PrivateRoute = () => {
  const { isAuthenticated, isBootstrapping } = useAuthStore();
  console.log("PrivateRoute:", { isAuthenticated, isBootstrapping });
  if (isBootstrapping) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <span className="material-symbols-outlined text-primary text-[48px] animate-spin">
            progress_activity
          </span>
          <p className="text-on-surface-variant text-sm">Cargando...</p>
        </div>
      </div>
    );
  }
 
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
};
 
export default PrivateRoute;
