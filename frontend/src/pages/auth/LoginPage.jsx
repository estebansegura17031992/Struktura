/**
 * LoginPage — Página de inicio de sesión (R-0102, R-0103, R-0104).
 *
 * Estructura fiel al mockup Struktura:
 *  - TopAppBar: logo + nav (Login activo, Sign Up)
 *  - Fondo: gradiente radial dual (naranja izq + cyan der)
 *  - Banner Rate Limit: ícono timer + countdown regresivo real (00:45)
 *  - Banner Email No Verificado: con link "Reenviar verificación"
 *  - Card: logo, "Bienvenido de nuevo", email con @, password con lock + toggle
 *  - Link "¿Olvidaste tu contraseña?" alineado derecha en el label
 *  - Botón: estado idle "Iniciar sesión" / loading "Verificando..." con spinner
 *  - Footer docked con borde superior
 *
 * Flujos:
 *  - 200 → setAuth(token, user) → navigate("/dashboard")
 *  - 403 EMAIL_NOT_VERIFIED → mostrar banner cyan + link reenviar
 *  - 429 → mostrar banner rojo con countdown de 45 segundos
 *  - 401 → error inline en la card
 */
import { useState, useEffect, useCallback } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { loginUser, resendVerification } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";
 
// ─── Helpers ──────────────────────────────────────────────────────────────────
 
const extractApiError = (err) => {
  const code  = err?.response?.data?.error?.code;
  const msg   = err?.response?.data?.error?.message;
  const status = err?.response?.status;
  if (status === 429)                       return { type: "rate_limit" };
  if (code === "EMAIL_NOT_VERIFIED")        return { type: "unverified" };
  if (code === "INVALID_CREDENTIALS")       return { type: "inline", message: "Email o contraseña incorrectos." };
  return { type: "inline", message: msg || "Error al iniciar sesión. Intenta de nuevo." };
};
 
// ─── Subcomponentes ───────────────────────────────────────────────────────────
 
/** Banner de rate limiting con countdown regresivo */
const RateLimitBanner = ({ onExpire }) => {
  const [seconds, setSeconds] = useState(45);
 
  useEffect(() => {
    if (seconds <= 0) { onExpire?.(); return; }
    const t = setTimeout(() => setSeconds((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [seconds, onExpire]);
 
  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
 
  return (
    <div className="mb-4 bg-error-container/20 border border-error/30 rounded-lg p-4 flex items-start gap-3">
      <span className="material-symbols-outlined text-error text-[20px] mt-0.5 flex-shrink-0">
        timer
      </span>
      <div className="flex-1">
        <p className="text-sm font-semibold text-error">Demasiados intentos</p>
        <p className="text-sm text-on-surface-variant mt-0.5">
          Por favor, espera{" "}
          <span className="font-bold text-on-surface">
            {mm}:{ss}
          </span>{" "}
          antes de intentar de nuevo.
        </p>
      </div>
    </div>
  );
};
 
/** Banner de email no verificado con link de reenvío */
const UnverifiedEmailBanner = ({ email, onResent }) => {
  const [resending, setResending] = useState(false);
  const [resentOk, setResentOk]   = useState(false);
 
  const handleResend = async (e) => {
    e.preventDefault();
    if (!email || resending) return;
    setResending(true);
    try {
      await resendVerification(email);
      setResentOk(true);
      onResent?.();
    } catch {
      // Silencioso — siempre retorna 200
      setResentOk(true);
    } finally {
      setResending(false);
    }
  };
 
  return (
    <div className="mb-4 bg-secondary-container/10 border border-secondary/30 rounded-lg p-4 flex items-start gap-3">
      <span className="material-symbols-outlined text-secondary text-[20px] mt-0.5 flex-shrink-0">
        mail
      </span>
      <div className="flex-1">
        <p className="text-sm font-semibold text-secondary">Correo no verificado</p>
        {resentOk ? (
          <p className="text-sm text-on-surface-variant mt-0.5">
            Código reenviado. Revisa tu bandeja de entrada.
          </p>
        ) : (
          <p className="text-sm text-on-surface-variant mt-0.5">
            Revisa tu bandeja de entrada o{" "}
            <button
              onClick={handleResend}
              disabled={resending}
              className="text-secondary font-semibold hover:underline decoration-2 underline-offset-4 disabled:opacity-60"
            >
              {resending ? "Enviando..." : "Reenviar verificación"}
            </button>
            .
          </p>
        )}
      </div>
    </div>
  );
};
 
// ─── Componente principal ─────────────────────────────────────────────────────
 
const LoginPage = () => {
  const navigate  = useNavigate();
  const location  = useLocation();
  const { setAuth } = useAuthStore();
 
  // Estado de banners
  const [showRateLimit,   setShowRateLimit]   = useState(false);
  const [showUnverified,  setShowUnverified]  = useState(false);
  const [unverifiedEmail, setUnverifiedEmail] = useState("");
  const [inlineError,     setInlineError]     = useState("");
  const [showPassword,    setShowPassword]    = useState(false);
  const [isSubmitting,    setIsSubmitting]    = useState(false);
 
  const {
    register,
    handleSubmit,
    formState: { errors },
    getValues,
  } = useForm();
 
  // Si viene de verify-email con email pre-cargado
  const prefillEmail = location.state?.email || "";
 
  const clearErrors = () => {
    setInlineError("");
    setShowRateLimit(false);
    setShowUnverified(false);
  };
 
  const onSubmit = async (data) => {
    clearErrors();
    setIsSubmitting(true);
    try {
      const res = await loginUser(data.email.trim().toLowerCase(), data.password);
      setAuth(res.access_token, res.user);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      const parsed = extractApiError(err);
      if (parsed.type === "rate_limit") {
        setShowRateLimit(true);
      } else if (parsed.type === "unverified") {
        setUnverifiedEmail(data.email.trim().toLowerCase());
        setShowUnverified(true);
      } else {
        setInlineError(parsed.message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };
 
  // ─── Render ─────────────────────────────────────────────────────────────────
 
  return (
    <div
      className="min-h-screen flex flex-col text-on-background font-['Inter']"
      style={{
        background:
          "radial-gradient(circle at 10% 20%, rgba(217,118,37,0.15) 0%, transparent 40%), radial-gradient(circle at 90% 80%, rgba(37,191,217,0.15) 0%, transparent 40%), #111316",
      }}
    >
      {/* ── TopAppBar ─────────────────────────────────────────────────────── */}
      <header className="bg-background/80 backdrop-blur-sm sticky top-0 z-50 border-b border-outline-variant/20">
        <div className="flex justify-between items-center px-12 py-3 w-full max-w-7xl mx-auto">
          <div className="flex items-center gap-2">
            {/* Logo hexagonal consistente con el design system */}
            <div className="w-8 h-8 bg-primary-container flex items-center justify-center rounded-full">
              <span
                className="material-symbols-outlined text-on-primary-container text-[18px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                hexagon
              </span>
            </div>
            <span
              className="font-['Poppins'] text-xl font-bold text-on-background"
            >
              Struktura
            </span>
          </div>
 
          <nav className="hidden md:flex gap-6 items-center">
            {/* Login activo — subrayado naranja */}
            <span className="text-primary font-bold border-b-2 border-primary pb-0.5 text-sm">
              Login
            </span>
            <Link
              to="/register"
              className="bg-primary-container text-on-primary-container px-6 py-2 rounded-full text-sm font-semibold hover:opacity-90 transition-opacity"
            >
              Sign Up
            </Link>
          </nav>
        </div>
      </header>
 
      {/* ── Contenido principal ───────────────────────────────────────────── */}
      <main className="flex-grow flex items-center justify-center px-4 py-12 relative overflow-hidden">
        {/* Esferas decorativas de fondo */}
        <div className="absolute top-1/4 -left-20 w-64 h-64 bg-primary opacity-10 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-1/4 -right-20 w-64 h-64 bg-secondary opacity-10 rounded-full blur-[100px] pointer-events-none" />
 
        <div className="w-full max-w-[420px] z-10">
 
          {/* Banner rate limiting */}
          {showRateLimit && (
            <RateLimitBanner onExpire={() => setShowRateLimit(false)} />
          )}
 
          {/* Banner email no verificado */}
          {showUnverified && (
            <UnverifiedEmailBanner
              email={unverifiedEmail}
              onResent={() => {}}
            />
          )}
 
          {/* ── Card de login ──────────────────────────────────────────────── */}
          <div className="bg-surface-container border border-outline-variant rounded-xl p-6 shadow-2xl backdrop-blur-sm">
 
            {/* Marca */}
            <div className="flex flex-col items-center mb-6">
              <div className="w-14 h-14 bg-primary-container flex items-center justify-center rounded-full mb-4 shadow-lg shadow-primary-container/20">
                <span
                  className="material-symbols-outlined text-on-primary-container text-[30px]"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  hexagon
                </span>
              </div>
              <h1 className="font-['Poppins'] text-2xl font-semibold text-on-surface mb-1">
                Bienvenido de nuevo
              </h1>
              <p className="text-sm text-on-surface-variant">
                Ingresa tus credenciales para continuar
              </p>
            </div>
 
            {/* Formulario */}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
 
              {/* Error inline (credenciales incorrectas) */}
              {inlineError && (
                <div className="flex items-center gap-2 bg-error-container/20 border border-error/30 rounded-lg px-4 py-3">
                  <span className="material-symbols-outlined text-error text-[18px] flex-shrink-0">
                    error_outline
                  </span>
                  <p className="text-sm text-on-error-container">{inlineError}</p>
                </div>
              )}
 
              {/* Campo EMAIL con ícono @ */}
              <div className="space-y-1">
                <label className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider block">
                  Email
                </label>
                <div className="relative group">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant group-focus-within:text-secondary transition-colors text-[20px]">
                    alternate_email
                  </span>
                  <input
                    type="email"
                    autoComplete="email"
                    defaultValue={prefillEmail}
                    placeholder="nombre@ejemplo.com"
                    className={`w-full bg-surface-container-low border rounded-lg py-3 pl-12 pr-4 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:border-secondary focus:ring-1 focus:ring-secondary transition-all outline-none ${
                      errors.email ? "border-error/60" : "border-outline-variant"
                    }`}
                    {...register("email", {
                      required: "El email es requerido",
                      pattern: {
                        value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                        message: "Formato de email inválido",
                      },
                      onChange: () => setInlineError(""),
                    })}
                  />
                </div>
                {errors.email && (
                  <p className="text-[11px] text-error ml-1">{errors.email.message}</p>
                )}
              </div>
 
              {/* Campo CONTRASEÑA con ícono lock + toggle show/hide */}
              <div className="space-y-1">
                {/* Label + link Olvidaste tu contraseña en la misma fila */}
                <div className="flex justify-between items-center">
                  <label className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider block">
                    Contraseña
                  </label>
                  <Link
                    to="/forgot-password"
                    className="text-[12px] text-secondary hover:text-secondary-fixed-dim transition-colors"
                  >
                    ¿Olvidaste tu contraseña?
                  </Link>
                </div>
                <div className="relative group">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant group-focus-within:text-secondary transition-colors text-[20px]">
                    lock
                  </span>
                  <input
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="••••••••"
                    className={`w-full bg-surface-container-low border rounded-lg py-3 pl-12 pr-12 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:border-secondary focus:ring-1 focus:ring-secondary transition-all outline-none ${
                      errors.password ? "border-error/60" : "border-outline-variant"
                    }`}
                    {...register("password", {
                      required: "La contraseña es requerida",
                      onChange: () => setInlineError(""),
                    })}
                  />
                  {/* Toggle show/hide */}
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
                    aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                  >
                    <span className="material-symbols-outlined text-[20px]">
                      {showPassword ? "visibility_off" : "visibility"}
                    </span>
                  </button>
                </div>
                {errors.password && (
                  <p className="text-[11px] text-error ml-1">{errors.password.message}</p>
                )}
              </div>
 
              {/* Botón submit — idle / loading */}
              <button
                type="submit"
                disabled={isSubmitting || showRateLimit}
                className="w-full bg-primary-container text-on-primary-container font-semibold text-sm py-4 rounded-full flex items-center justify-center gap-2 mt-2 hover:opacity-90 active:scale-[0.98] transition-all disabled:opacity-60 disabled:cursor-not-allowed disabled:active:scale-100"
              >
                {isSubmitting ? (
                  <>
                    {/* Spinner fiel al mockup — css puro */}
                    <div
                      className="w-4 h-4 rounded-full border-2 border-on-primary-container/30 border-t-on-primary-container animate-spin flex-shrink-0"
                    />
                    <span>Verificando...</span>
                  </>
                ) : (
                  <>
                    <span>Iniciar sesión</span>
                    <span className="material-symbols-outlined text-[20px]">
                      arrow_forward
                    </span>
                  </>
                )}
              </button>
 
              {/* Separador + link registro */}
              <div className="pt-4 text-center border-t border-outline-variant/30 mt-4">
                <p className="text-sm text-on-surface-variant">
                  ¿No tienes cuenta?{" "}
                  <Link
                    to="/register"
                    className="text-secondary font-semibold hover:underline decoration-2 underline-offset-4 ml-1"
                  >
                    Regístrate
                  </Link>
                </p>
              </div>
            </form>
          </div>
 
          {/* Flecha decorativa inferior — fiel al mockup */}
          <div className="mt-6 flex justify-center opacity-30">
            <span
              className="material-symbols-outlined text-secondary"
              style={{ fontSize: "32px" }}
            >
              trending_flat
            </span>
          </div>
        </div>
      </main>
 
      {/* ── Footer docked ─────────────────────────────────────────────────── */}
      <footer className="bg-background border-t border-outline-variant/30">
        <div className="flex flex-col md:flex-row justify-between items-center px-12 py-6 w-full max-w-7xl mx-auto">
          <span className="text-[12px] font-medium text-on-surface-variant order-2 md:order-1 mt-4 md:mt-0">
            © 2024 Struktura. All rights reserved.
          </span>
          <div className="flex gap-6 order-1 md:order-2">
            {["Terms", "Privacy", "Security Status"].map((link) => (
              <a
                key={link}
                href="#"
                className="text-[12px] font-medium text-on-surface-variant hover:text-secondary transition-colors"
              >
                {link}
              </a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
};
 
export default LoginPage;
