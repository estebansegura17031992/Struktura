/**
 * SessionsSection — Sesiones activas (R-0104).
 * Muestra refresh tokens activos con dispositivo, fecha, IP.
 * Botón "Revocar" por sesión + "Revocar todas las sesiones".
 * En MVP: el backend no expone endpoint GET /sessions, así que se muestran
 * datos simulados del store. Se implementará completamente en Sprint 2.
 * El botón "Revocar" llama POST /auth/logout de la sesión actual.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { logoutUser } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";
 
const SESSION_ICON = {
  desktop: "desktop_mac",
  mobile:  "smartphone",
  tablet:  "tablet",
};
 
const SessionsSection = () => {
  const navigate   = useNavigate();
  const { clearAuth, user } = useAuthStore();
  const [revoking, setRevoking] = useState(false);
 
  // MVP: sesión actual simulada — en Sprint 2 se obtiene de GET /auth/sessions
  const currentSession = {
    id:         "current",
    device:     "Este dispositivo",
    icon:       "desktop",
    created_at: new Date().toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" }),
    ip:         "localhost",
    isCurrent:  true,
  };
 
  const handleRevokeAll = async () => {
    if (!confirm("¿Revocar todas las sesiones? Se cerrará esta sesión también.")) return;
    setRevoking(true);
    try {
      await logoutUser();
    } catch { } finally {
      clearAuth();
      navigate("/login");
    }
  };
 
  const handleRevokeCurrent = async () => {
    setRevoking(true);
    try {
      await logoutUser();
    } catch { } finally {
      clearAuth();
      navigate("/login");
    }
  };
 
  return (
    <section
      className="rounded-xl p-8 mb-6"
      style={{ background: "rgba(30,32,35,0.8)", backdropFilter: "blur(12px)", border: "1px solid #2D3135" }}
    >
      <div className="flex justify-between items-center mb-6">
        <h2 className="font-['Poppins'] text-xl font-semibold text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[22px]">devices</span>
          Sesiones activas
        </h2>
        <button
          onClick={handleRevokeAll}
          disabled={revoking}
          className="text-error text-sm font-medium underline hover:opacity-70 transition-opacity disabled:opacity-40"
        >
          Revocar todas las sesiones
        </button>
      </div>
 
      {/* Nota de MVP */}
      <div className="mb-4 flex items-start gap-2 bg-secondary/5 border border-secondary/20 rounded-lg px-4 py-3">
        <span className="material-symbols-outlined text-secondary text-[16px] mt-0.5 flex-shrink-0">info</span>
        <p className="text-xs text-on-surface-variant">
          Vista detallada de sesiones disponible en Sprint 2. Por ahora puedes cerrar la sesión actual.
        </p>
      </div>
 
      {/* Sesión actual */}
      <div className="space-y-3">
        <div
          className="flex items-center justify-between p-4 rounded-xl border border-outline-variant/30"
          style={{ background: "rgba(30,32,35,1)" }}
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-surface-variant flex items-center justify-center rounded-full">
              <span className="material-symbols-outlined text-secondary">
                {SESSION_ICON[currentSession.icon]}
              </span>
            </div>
            <div>
              <p className="text-sm font-semibold text-on-surface">{currentSession.device}</p>
              <p className="text-xs text-on-surface-variant">
                Sesión activa • {user?.email || ""}
              </p>
            </div>
          </div>
          <button
            onClick={handleRevokeCurrent}
            disabled={revoking}
            className="px-4 py-2 rounded-full text-sm text-on-surface hover:bg-surface-variant transition-colors disabled:opacity-40"
            style={{ background: "#37393d" }}
          >
            {revoking ? "..." : "Cerrar sesión"}
          </button>
        </div>
      </div>
    </section>
  );
};
 
export default SessionsSection;
