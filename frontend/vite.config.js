import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
 
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Alias @ → src/  para que todos los imports usen rutas absolutas
      // Ejemplo: import { useAuthStore } from "@/store/authStore"
      // Vite resuelve siempre al mismo archivo físico → un solo módulo → un solo store
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
