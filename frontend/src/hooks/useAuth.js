/**
 * Hook centralizado para acciones de autenticación.
 * Encapsula las llamadas a la API y actualiza el store.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import {
  registerUser,
  loginUser,
  logoutUser,
  getMe,
} from "@/api/auth";
 
export const useRegister = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
 
  const register = async (formData) => {
    setLoading(true);
    setError(null);
    try {
      await registerUser(formData);
      // Redirigir a verificación pasando el email en state
      navigate("/verify-email", { state: { email: formData.email } });
    } catch (err) {
      const apiError = err.response?.data?.error;
      setError(apiError?.message || "Error al crear la cuenta. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  };
 
  return { register, loading, error, setError };
};
 
export const useLogin = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();
 
  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const data = await loginUser(email, password);
      setAuth(data.access_token, data.user);
      navigate("/dashboard");
    } catch (err) {
      const code = err.response?.data?.error?.code;
      const message = err.response?.data?.error?.message;
      if (code === "EMAIL_NOT_VERIFIED") {
        navigate("/verify-email", { state: { email } });
        return;
      }
      setError(message || "Credenciales incorrectas.");
    } finally {
      setLoading(false);
    }
  };
 
  return { login, loading, error, setError };
};
 
export const useLogout = () => {
  const { clearAuth } = useAuthStore();
  const navigate = useNavigate();
 
  const logout = async () => {
    try {
      await logoutUser();
    } catch {
      // Limpiar estado local aunque falle el backend
    } finally {
      clearAuth();
      navigate("/login");
    }
  };
 
  return { logout };
};
