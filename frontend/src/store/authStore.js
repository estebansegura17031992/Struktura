/**
 * Zustand auth store — con persistencia en sessionStorage.
 *
 * Por qué sessionStorage y no memoria pura:
 * Zustand en memoria se resetea cuando React re-monta el árbol de componentes
 * (navegar entre rutas con lazy loading, HMR en dev, etc.).
 * sessionStorage persiste durante la sesión del tab pero se borra al cerrarlo,
 * lo que es aceptable para el accessToken (expira en 15 min de todas formas).
 *
 * El refresh token sigue en cookie HttpOnly — no cambia nada en seguridad.
 *
 * NOTA: En producción el accessToken en sessionStorage es aceptable porque:
 *  - Expira en 15 min
 *  - Solo accesible desde el mismo tab/origen
 *  - Se borra al cerrar el tab
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
 
const useAuthStore = create(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      isBootstrapping: false,
 
      setAuth: (token, user) =>
        set({
          accessToken: token,
          user,
          isAuthenticated: true,
          isBootstrapping: false,
        }),
 
      setAccessToken: (token) =>
        set({ accessToken: token }),
 
      clearAuth: () =>
        set({
          accessToken: null,
          user: null,
          isAuthenticated: false,
          isBootstrapping: false,
        }),
 
      setBootstrapping: (value) =>
        set({ isBootstrapping: value }),
    }),
    {
      name: "struktura-auth",           // clave en sessionStorage
      storage: createJSONStorage(() => sessionStorage),
      // Solo persistir lo necesario — NO persistir isBootstrapping
      partialize: (state) => ({
        accessToken: state.accessToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
 
// Exponer en window para el interceptor de axios
if (typeof window !== "undefined") {
  window.__authStore = useAuthStore;
}
 
export { useAuthStore };
export default useAuthStore;
