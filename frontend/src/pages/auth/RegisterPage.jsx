/**
 * RegisterPage — Página de registro (R-0101, AG-01, AG-02).
 *
 * Implementa el mockup del design system Struktura:
 *  - Fondo atmosférico con gradiente y esferas de color difuminado
 *  - Card central con logo hexagonal, campos pill-shaped
 *  - Grid 2 columnas (Nombre + Usuario), Email, Contraseña + StrengthMeter
 *  - Timezone detectada automáticamente con Intl.DateTimeFormat (AG-02)
 *  - Banner de invitación (solo si hay ?invitation_token en la URL)
 *  - Banner de error (rate limiting 429)
 *  - Estados: idle, loading, error, success
 *
 * Flujo tras registro exitoso:
 *   → navigate("/verify-email", { state: { email } })
 *
 * Validaciones client-side (react-hook-form + reglas de negocio del PRD):
 *   - username: 3-30 chars, /^[a-zA-Z0-9_]+$/
 *   - email: formato válido
 *   - password: ≥8 chars, al menos 1 dígito
 *   - terms: requerido
 */
import { useEffect, useState, useRef } from "react";
import { useForm } from "react-hook-form";
import { Link, useSearchParams } from "react-router-dom";
import { registerUser } from "@/api/auth";
import StrengthMeter from "@/components/ui/StrengthMeter";
import ErrorBanner from "@/components/ui/ErrorBanner";
import InvitationBanner from "@/components/ui/InvitationBanner";
 
// ─── Helpers ──────────────────────────────────────────────────────────────────
 
/**
 * Lee la timezone local del navegador (AG-02).
 * Fallback a "UTC" si el API no está disponible.
 */
const detectTimezone = () => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
};
 
/**
 * Extrae el mensaje de error legible de una respuesta de axios.
 * El backend siempre retorna { error: { code, message } }.
 */
const extractApiError = (err) => {
  const code = err?.response?.data?.error?.code;
  const message = err?.response?.data?.error?.message;
  const status = err?.response?.status;
 
  if (status === 429) {
    return "Demasiados intentos. Por favor, inténtalo de nuevo en unos minutos.";
  }
  if (code === "EMAIL_ALREADY_EXISTS") return "Este email ya está registrado.";
  if (code === "USERNAME_ALREADY_EXISTS") return "Este nombre de usuario ya está en uso.";
  if (code === "INVALID_TIMEZONE") return "Zona horaria no reconocida. Contacta soporte.";
  return message || "Error al crear la cuenta. Intenta de nuevo.";
};
 
// ─── Componente principal ─────────────────────────────────────────────────────
 
const RegisterPage = ({ onSuccess }) => {
  const [searchParams] = useSearchParams();
  const invitationToken = searchParams.get("invitation_token");
  const invitedEmail = searchParams.get("email"); // Pre-filled desde la invitación
  const invitedProject = searchParams.get("project"); // Nombre del proyecto para el banner
 
  const [globalError, setGlobalError] = useState(null);
  const [isRateLimited, setIsRateLimited] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [passwordValue, setPasswordValue] = useState("");
 
  const timezone = useRef(detectTimezone());
 
  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm({
    defaultValues: {
      email: invitedEmail || "",
    },
  });
 
  // Pre-cargar email de invitación si viene en la URL
  useEffect(() => {
    if (invitedEmail) setValue("email", invitedEmail);
  }, [invitedEmail, setValue]);
 
  const onSubmit = async (data) => {
    setIsSubmitting(true);
    setGlobalError(null);
    setIsRateLimited(false);
 
    try {
      await registerUser({
        username: data.username.trim().toLowerCase(),
        email: data.email.trim().toLowerCase(),
        password: data.password,
        full_name: data.full_name?.trim() || undefined,
        timezone: timezone.current,
        // Si viene de invitación, incluir el token para que el backend lo procese
        ...(invitationToken && { invitation_token: invitationToken }),
      });
 
      // Éxito: redirigir a verificación de email
      if (onSuccess) {
        onSuccess(data.email);
      } else {
        // Fallback si no hay router provider en tests
        window.location.href = `/verify-email?email=${encodeURIComponent(data.email)}`;
      }
    } catch (err) {
      const errorMessage = extractApiError(err);
      if (err?.response?.status === 429) {
        setIsRateLimited(true);
      }
      setGlobalError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };
 
  // ─── Render ─────────────────────────────────────────────────────────────────
 
  return (
    <div className="bg-background text-on-background min-h-screen flex flex-col font-['Inter'] overflow-x-hidden">
 
      {/* Fondo atmosférico — 3 capas como en el mockup */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute inset-0 bg-gradient-to-br from-surface-container-lowest via-background to-surface-container-low" />
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[500px] h-[500px] bg-secondary/5 rounded-full blur-[120px]" />
      </div>
 
      {/* Banner rate limiting (429) */}
      {isRateLimited && (
        <ErrorBanner
          message="Demasiados intentos. Por favor, inténtalo de nuevo en unos minutos."
          onDismiss={() => setIsRateLimited(false)}
        />
      )}
 
      {/* Banner de invitación a proyecto */}
      {invitedProject && <InvitationBanner projectName={decodeURIComponent(invitedProject)} />}
 
      {/* Contenido principal */}
      <main className="relative z-10 flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-[440px] bg-surface-container border border-outline-variant/30 rounded-[2rem] p-12 shadow-2xl backdrop-blur-sm">
 
          {/* Marca / Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-12 h-12 bg-primary-container flex items-center justify-center rounded-full mb-4 shadow-lg shadow-primary-container/20">
              <span
                className="material-symbols-outlined text-on-primary-container text-[28px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                hexagon
              </span>
            </div>
            <h1 className="font-['Poppins'] text-2xl font-semibold text-on-surface mb-1">
              Crear cuenta
            </h1>
            <p className="text-sm text-on-surface-variant text-center">
              Únete a Struktura para organizar tu flujo de trabajo.
            </p>
          </div>
 
          {/* Formulario */}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
 
            {/* Error general de API (no 429) */}
            {globalError && !isRateLimited && (
              <div className="flex items-center gap-2 bg-error-container/20 border border-error/30 rounded-2xl px-4 py-3">
                <span className="material-symbols-outlined text-error text-[18px]">
                  error_outline
                </span>
                <p className="text-sm text-on-error-container">{globalError}</p>
              </div>
            )}
 
            {/* Fila 2 columnas: Nombre Completo + Usuario */}
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-1">
                <label
                  className="text-[12px] font-medium text-on-surface-variant uppercase tracking-wider block ml-1"
                  htmlFor="full_name"
                >
                  Nombre Completo
                </label>
                <input
                  id="full_name"
                  type="text"
                  placeholder="Nombre Apellido"
                  className={`w-full bg-surface-container-low border rounded-full px-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 transition-all focus:outline-none focus:ring-2 focus:ring-secondary/20 ${
                    errors.full_name
                      ? "border-error/60"
                      : "border-outline-variant"
                  }`}
                  {...register("full_name")}
                />
                {/* full_name es opcional — no se muestra error */}
              </div>
 
              <div className="space-y-1">
                <label
                  className="text-[12px] font-medium text-on-surface-variant uppercase tracking-wider block ml-1"
                  htmlFor="username"
                >
                  Usuario
                </label>
                <input
                  id="username"
                  type="text"
                  placeholder="miusuario"
                  autoComplete="username"
                  className={`w-full bg-surface-container-low border rounded-full px-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 transition-all focus:outline-none focus:ring-2 focus:ring-secondary/20 ${
                    errors.username ? "border-error/60" : "border-outline-variant"
                  }`}
                  {...register("username", {
                    required: "El usuario es requerido",
                    minLength: { value: 3, message: "Mínimo 3 caracteres" },
                    maxLength: { value: 30, message: "Máximo 30 caracteres" },
                    pattern: {
                      value: /^[a-zA-Z0-9_]+$/,
                      message: "Solo letras, números y guiones bajos",
                    },
                  })}
                />
                {errors.username && (
                  <p className="text-[11px] text-error ml-1 mt-0.5">
                    {errors.username.message}
                  </p>
                )}
              </div>
            </div>
 
            {/* Email — readonly si viene de invitación, editable en registro normal */}
            <div className="space-y-1">
              <label
                className="text-[12px] font-medium text-on-surface-variant uppercase tracking-wider block ml-1"
                htmlFor="email"
              >
                Correo Electrónico
              </label>
              <div className="relative">
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  readOnly={!!invitedEmail}
                  className={`w-full border rounded-full px-4 py-3 text-sm text-on-surface transition-all focus:outline-none ${
                    invitedEmail
                      ? "bg-surface-container-lowest border-outline-variant/50 opacity-80 cursor-not-allowed"
                      : errors.email
                      ? "bg-surface-container-low border-error/60 focus:ring-2 focus:ring-secondary/20"
                      : "bg-surface-container-low border-outline-variant focus:ring-2 focus:ring-secondary/20"
                  }`}
                  {...register("email", {
                    required: "El email es requerido",
                    pattern: {
                      value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                      message: "Formato de email inválido",
                    },
                  })}
                />
                {/* Icono de candado si el email viene de una invitación */}
                {invitedEmail && (
                  <span
                    className="absolute right-4 top-1/2 -translate-y-1/2 material-symbols-outlined text-[18px] text-primary"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    lock
                  </span>
                )}
              </div>
              {errors.email && !invitedEmail && (
                <p className="text-[11px] text-error ml-1 mt-0.5">
                  {errors.email.message}
                </p>
              )}
            </div>
 
            {/* Contraseña + StrengthMeter */}
            <div className="space-y-1">
              <label
                className="text-[12px] font-medium text-on-surface-variant uppercase tracking-wider block ml-1"
                htmlFor="password"
              >
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                className={`w-full bg-surface-container-low border rounded-full px-4 py-3 text-sm text-on-surface transition-all focus:outline-none focus:ring-2 focus:ring-secondary/20 ${
                  errors.password ? "border-error/60" : "border-outline-variant"
                }`}
                {...register("password", {
                  required: "La contraseña es requerida",
                  minLength: { value: 8, message: "Mínimo 8 caracteres" },
                  validate: (v) =>
                    /\d/.test(v) || "Debe contener al menos un número",
                  onChange: (e) => setPasswordValue(e.target.value),
                })}
              />
              <StrengthMeter value={passwordValue} />
              {errors.password && (
                <p className="text-[11px] text-error ml-1 -mt-2">
                  {errors.password.message}
                </p>
              )}
            </div>
 
            {/* Campo oculto de timezone (AG-02) */}
            <input type="hidden" value={timezone.current} {...register("timezone")} />
 
            {/* Nota de timezone detectada automáticamente */}
            <div className="flex items-start gap-2 ml-1 opacity-60">
              <span className="material-symbols-outlined text-[16px] mt-0.5">info</span>
              <p className="text-[12px] text-on-surface-variant leading-tight">
                Tu zona horaria se detectó automáticamente. Puedes cambiarla en tu perfil.
              </p>
            </div>
 
            {/* Términos y condiciones */}
            <div className="flex items-center gap-3 pt-2 ml-1">
              <input
                id="terms"
                type="checkbox"
                className="w-5 h-5 rounded bg-surface-container-low border-outline-variant text-secondary focus:ring-secondary/20 cursor-pointer transition-all"
                {...register("terms", {
                  required: "Debes aceptar los términos para continuar",
                })}
              />
              <label
                className="text-sm text-on-surface-variant cursor-pointer select-none"
                htmlFor="terms"
              >
                Acepto los{" "}
                <a
                  href="#"
                  className="text-secondary hover:underline underline-offset-4"
                  onClick={(e) => e.stopPropagation()}
                >
                  Términos y Condiciones
                </a>
              </label>
            </div>
            {errors.terms && (
              <p className="text-[11px] text-error ml-1 -mt-2">
                {errors.terms.message}
              </p>
            )}
 
            {/* Botón submit */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-primary-container text-on-primary-container font-semibold text-sm py-4 rounded-full shadow-lg shadow-primary-container/20 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2 mt-4 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:scale-100"
            >
              {isSubmitting ? (
                <>
                  <span className="material-symbols-outlined text-[20px] animate-spin">
                    progress_activity
                  </span>
                  <span>Creando cuenta...</span>
                </>
              ) : (
                <>
                  <span>Crear cuenta</span>
                  <span className="material-symbols-outlined text-[20px]">
                    arrow_forward
                  </span>
                </>
              )}
            </button>
          </form>
 
          {/* Link a login */}
          <div className="mt-8 text-center">
            <Link
              to="/login"
              className="text-sm text-on-surface-variant hover:text-secondary transition-colors inline-flex items-center gap-1 group"
            >
              ¿Ya tienes cuenta?{" "}
              <span className="text-secondary font-semibold group-hover:underline underline-offset-4">
                Inicia sesión
              </span>
            </Link>
          </div>
        </div>
      </main>
 
      {/* Footer */}
      <footer className="relative z-10 w-full max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center px-12 py-8 border-t border-outline-variant/20">
        <div className="text-on-surface-variant text-sm mb-4 md:mb-0">
          © 2024 Struktura. All rights reserved.
        </div>
        <div className="flex gap-6">
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
      </footer>
    </div>
  );
};
 
export default RegisterPage;
