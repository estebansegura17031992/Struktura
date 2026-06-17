/**
 * App.jsx — Bootstrap simplificado.
 *
 * Con sessionStorage persistence en Zustand, el accessToken sobrevive
 * la navegación entre rutas. El bootstrap ahora solo se ejecuta cuando
 * NO hay token en el store (primera visita o tab nuevo).
 */
import { useEffect, useRef, useState } from "react";
import AppRouter from "@/router/AppRouter";
import { useAuthStore } from "@/store/authStore";
import { refreshToken, getMe } from "@/api/auth";

const App = () => {
  const { setAuth, clearAuth, isAuthenticated, accessToken } = useAuthStore();
  const [hydrated, setHydrated] = useState(useAuthStore.persist.hasHydrated());
  const [bootstrapping, setBootstrapping] = useState(!isAuthenticated);
  const [connectionError, setConnectionError] = useState(false);
  const ran = useRef(false);

  // Esperar hidratación de Zustand persist
  useEffect(() => {
    const unsub = useAuthStore.persist.onFinishHydration(() => setHydrated(true));
    if (useAuthStore.persist.hasHydrated()) setHydrated(true);
    return unsub;
  }, []);

  useEffect(() => {
    if (!hydrated) return; // no arrancar bootstrap hasta hidratar

    if (isAuthenticated && accessToken) {
      setBootstrapping(false);
      return;
    }

    if (ran.current) return;
    ran.current = true;

    const run = async () => {
      setBootstrapping(true);
      try {
        const tokenData = await refreshToken();
        const userData  = await getMe();
        setAuth(tokenData.access_token, userData);
      } catch (err) {
        const status = err?.response?.status;
        if (status === 401 || status === 403) {
          clearAuth();
        } else {
          clearAuth();
          if (!status) setConnectionError(true);
        }
      } finally {
        setBootstrapping(false);
      }
    };

    run();
  }, [hydrated]);

  // Bloquear render hasta hidratar
  if (!hydrated || bootstrapping) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 bg-primary-container flex items-center justify-center rounded-full shadow-lg">
            <span className="material-symbols-outlined text-on-primary-container text-[28px]"
              style={{ fontVariationSettings: "'FILL' 1" }}>hexagon</span>
          </div>
          <div className="w-8 h-8 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
        </div>
      </div>
    );
  }

  if (connectionError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <div className="bg-surface-container border border-outline-variant/30 rounded-xl p-10 max-w-sm w-full text-center">
          <span className="material-symbols-outlined text-error text-[48px] mb-4 block">wifi_off</span>
          <h2 className="font-['Poppins'] text-xl font-semibold text-on-surface mb-2">Error de conexión</h2>
          <p className="text-sm text-on-surface-variant mb-6">No se pudo conectar con el servidor.</p>
          <button
            onClick={() => { ran.current = false; setConnectionError(false); }}
            className="bg-primary-container text-on-primary font-semibold text-sm py-3 px-8 rounded-full hover:opacity-90 transition-all"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return <AppRouter />;
};

export default App;