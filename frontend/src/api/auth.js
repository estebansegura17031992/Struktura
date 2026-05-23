/**
 * Funciones de API para autenticación (E01 — Sprint 1).
 * refreshToken usa withCredentials:true para enviar la cookie HttpOnly.
 */
import api from "./axiosInstance";
import axios from "axios";
 
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
 
export const registerUser = (data) =>
  api.post("/auth/register", data).then((r) => r.data);
 
export const verifyEmail = (email, code) =>
  api.post("/auth/verify-email", { email, code }).then((r) => r.data);
 
export const resendVerification = (email) =>
  api.post("/auth/resend-verification", { email }).then((r) => r.data);
 
export const loginUser = (email, password) =>
  api.post("/auth/login", { email, password }).then((r) => r.data);
 
/**
 * R-0103 — Silent refresh.
 * CRÍTICO: withCredentials:true para que el navegador envíe la cookie HttpOnly.
 * Usa axios directo (no la instancia interceptada) para evitar bucle infinito.
 */
export const refreshToken = () =>
  axios
    .post(`${BASE_URL}/auth/refresh`, {}, { withCredentials: true })
    .then((r) => r.data);
 
export const logoutUser = () =>
  api.post("/auth/logout").then((r) => r.data);
 
export const forgotPassword = (email) =>
  api.post("/auth/forgot-password", { email }).then((r) => r.data);
 
export const resetPassword = (token, new_password) =>
  api.post("/auth/reset-password", { token, new_password }).then((r) => r.data);
 
export const getMe = () =>
  api.get("/users/me").then((r) => r.data);
 
export const updateMe = (data) =>
  api.patch("/users/me", data).then((r) => r.data);
 
export const changePassword = (current_password, new_password) =>
  api
    .post("/users/me/change-password", { current_password, new_password })
    .then((r) => r.data);
