/**
 * AdminRoute — Solo accesible para usuarios con rol "admin".
 * Redirige a /dashboard si autenticado pero sin rol admin.
 * Redirige a /login si no autenticado.
 */
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

const AdminRoute = () => {
  const { isAuthenticated, isBootstrapping, user } = useAuthStore();

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

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (user?.role !== "admin") return <Navigate to="/dashboard" replace />;

  return <Outlet />;
};

export default AdminRoute;