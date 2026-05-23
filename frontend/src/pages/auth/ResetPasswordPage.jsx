/**
 * ResetPasswordPage — Restablecer contraseña con token (R-0105).
 *
 * Recibe el token desde query param: /reset-password?token=XXX
 * Mismo estilo visual que ForgotPasswordPage (card centrada, mismo fondo).
 *
 * Estados:
 *   "form"    → formulario nueva contraseña + confirmar
 *   "success" → confirmación con check_circle + link a login
 *   "invalid" → token inválido/expirado con mensaje y link a forgot-password
 *
 * Fiel al design system Struktura:
 *  - Ícono lock_open naranja en círculo
 *  - Inputs con ícono lock / visibility toggle
 *  - StrengthMeter reutilizado del Register
 *  - Botón primary-container → hover primary
 */
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resetPassword } from "@/api/auth";
import StrengthMeter from "@/components/ui/StrengthMeter";
 
// ─── Helpers ──────────────────────────────────────────────────────────────────
const extractError = (err) => {
  const code = err?.response?.data?.error?.code;
  if (code === "TOKEN_INVALID" || code === "TOKEN_EXPIRED")
    return { type: "invalid_token" };
  return { type: "generic", message: err?.response?.data?.error?.message || "Error al restablecer la contraseña." };
};
 
// ─── Componente principal ─────────────────────────────────────────────────────
const ResetPasswordPage = () => {
  const [searchParams]             = useSearchParams();
  const navigate                   = useNavigate();
  const token                      = searchParams.get("token") || "";
 
  const [uiState, setUiState]      = useState(token ? "form" : "invalid");
  const [transitioning, setTrans]  = useState(false);
  const [isSubmitting, setSubmit]  = useState(false);
  const [genericError, setGenErr]  = useState("");
  const [showPass, setShowPass]    = useState(false);
  const [showConfirm, setShowConf] = useState(false);
  const [passValue, setPassValue]  = useState("");
 
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm();
 
  const newPassword = watch("new_password", "");
 
  // ── Transición animada ───────────────────────────────────────────────────────
  const transitionTo = (next) => {
    setTrans(true);
    setTimeout(() => { setUiState(next); setTrans(false); }, 300);
  };
 
  const cardClass = `transition-all duration-300 ${
    transitioning ? "opacity-0 scale-95" : "opacity-100 scale-100"
  }`;
 
  // ── Submit ───────────────────────────────────────────────────────────────────
  const onSubmit = async (data) => {
    setSubmit(true);
    setGenErr("");
    try {
      await resetPassword(token, data.new_password);
      transitionTo("success");
      // Redirigir al login tras 3s
      setTimeout(() => navigate("/login", { state: { passwordReset: true } }), 3000);
    } catch (err) {
      const parsed = extractError(err);
      if (parsed.type === "invalid_token") {
        transitionTo("invalid");
      } else {
        setGenErr(parsed.message);
      }
    } finally {
      setSubmit(false);
    }
  };
 
  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center p-6 font-['Inter'] text-on-background"
      style={{
        background:
          "radial-gradient(circle at top right, rgba(217,118,37,0.15), transparent), " +
          "radial-gradient(circle at bottom left, rgba(37,191,217,0.15), transparent), " +
          "#0F1113",
      }}
    >
      <main className="w-full max-w-[400px]">
        <div
          className="border border-outline-variant/30 rounded-xl p-8 shadow-2xl overflow-hidden"
          style={{ background: "rgba(28,31,34,0.7)", backdropFilter: "blur(12px)" }}
        >
 
          {/* ── Estado: formulario ──────────────────────────────────────────── */}
          {uiState === "form" && (
            <div className={cardClass}>
              <div className="flex flex-col items-center text-center mb-6">
 
                {/* Ícono */}
                <div className="w-16 h-16 rounded-full flex items-center justify-center mb-6"
                  style={{
                    background: "rgba(218,119,38,0.1)",
                    border: "1px solid rgba(255,183,134,0.2)",
                  }}
                >
                  <span className="material-symbols-outlined text-primary text-[32px]">
                    lock_open
                  </span>
                </div>
 
                <h1 className="font-['Poppins'] text-2xl font-semibold text-on-surface mb-2">
                  Nueva contraseña
                </h1>
                <p className="text-sm text-on-surface-variant">
                  Elige una contraseña segura para tu cuenta.
                </p>
              </div>
 
              {/* Error genérico */}
              {genericError && (
                <div className="mb-4 flex items-center gap-2 bg-error-container/20 border border-error/30 rounded-lg px-4 py-3">
                  <span className="material-symbols-outlined text-error text-[18px] flex-shrink-0">
                    error_outline
                  </span>
                  <p className="text-sm text-on-error-container">{genericError}</p>
                </div>
              )}
 
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
 
                {/* Nueva contraseña */}
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider block">
                    Nueva contraseña
                  </label>
                  <div className="relative group">
                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant group-focus-within:text-secondary transition-colors text-[20px]">
                      lock
                    </span>
                    <input
                      type={showPass ? "text" : "password"}
                      autoComplete="new-password"
                      placeholder="••••••••"
                      className={`w-full bg-surface-container-high border rounded-lg py-3 pl-12 pr-12 text-sm text-on-surface placeholder:text-on-surface-variant/30 focus:outline-none focus:border-secondary transition-all ${
                        errors.new_password ? "border-error/60" : "border-outline-variant/50"
                      }`}
                      {...register("new_password", {
                        required: "La contraseña es requerida",
                        minLength: { value: 8, message: "Mínimo 8 caracteres" },
                        validate: (v) => /\d/.test(v) || "Debe contener al menos un número",
                        onChange: (e) => setPassValue(e.target.value),
                      })}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPass((v) => !v)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
                      aria-label={showPass ? "Ocultar" : "Mostrar"}
                    >
                      <span className="material-symbols-outlined text-[20px]">
                        {showPass ? "visibility_off" : "visibility"}
                      </span>
                    </button>
                  </div>
                  <StrengthMeter value={passValue} />
                  {errors.new_password && (
                    <p className="text-[11px] text-error ml-1 -mt-2">
                      {errors.new_password.message}
                    </p>
                  )}
                </div>
 
                {/* Confirmar contraseña */}
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider block">
                    Confirmar contraseña
                  </label>
                  <div className="relative group">
                    <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant group-focus-within:text-secondary transition-colors text-[20px]">
                      lock_reset
                    </span>
                    <input
                      type={showConfirm ? "text" : "password"}
                      autoComplete="new-password"
                      placeholder="••••••••"
                      className={`w-full bg-surface-container-high border rounded-lg py-3 pl-12 pr-12 text-sm text-on-surface placeholder:text-on-surface-variant/30 focus:outline-none focus:border-secondary transition-all ${
                        errors.confirm_password ? "border-error/60" : "border-outline-variant/50"
                      }`}
                      {...register("confirm_password", {
                        required: "Confirma tu contraseña",
                        validate: (v) =>
                          v === newPassword || "Las contraseñas no coinciden",
                      })}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConf((v) => !v)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
                      aria-label={showConfirm ? "Ocultar" : "Mostrar"}
                    >
                      <span className="material-symbols-outlined text-[20px]">
                        {showConfirm ? "visibility_off" : "visibility"}
                      </span>
                    </button>
                  </div>
                  {errors.confirm_password && (
                    <p className="text-[11px] text-error ml-1 mt-0.5">
                      {errors.confirm_password.message}
                    </p>
                  )}
                </div>
 
                {/* Botón */}
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-primary-container hover:bg-primary text-on-primary font-semibold text-sm py-4 rounded-full transition-all active:scale-[0.98] shadow-lg shadow-primary/10 mt-2 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-4 h-4 rounded-full border-2 border-on-primary/30 border-t-on-primary animate-spin flex-shrink-0" />
                      <span>Guardando...</span>
                    </>
                  ) : (
                    <>
                      <span>Restablecer contraseña</span>
                      <span className="material-symbols-outlined text-[18px]">
                        arrow_forward
                      </span>
                    </>
                  )}
                </button>
              </form>
 
              <div className="mt-6 text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 text-[12px] font-medium text-on-surface-variant hover:text-secondary transition-colors group"
                >
                  <span className="material-symbols-outlined text-[18px] group-hover:-translate-x-1 transition-transform">
                    arrow_back
                  </span>
                  Volver al login
                </Link>
              </div>
            </div>
          )}
 
          {/* ── Estado: éxito ────────────────────────────────────────────────── */}
          {uiState === "success" && (
            <div className={`${cardClass} flex flex-col items-center text-center py-8`}>
              <div className="w-20 h-20 rounded-full flex items-center justify-center mb-8 relative"
                style={{
                  background: "rgba(76,215,242,0.1)",
                  border: "1px solid rgba(76,215,242,0.2)",
                }}
              >
                <span
                  className="material-symbols-outlined text-secondary text-[40px]"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  check_circle
                </span>
                <div className="absolute inset-0 rounded-full border border-secondary/40 animate-ping opacity-20" />
              </div>
 
              <h2 className="font-['Poppins'] text-2xl font-semibold text-on-surface mb-3">
                ¡Contraseña actualizada!
              </h2>
              <p className="text-base text-on-surface-variant mb-2">
                Tu contraseña ha sido restablecida correctamente.
              </p>
              <p className="text-sm text-on-surface-variant/60">
                Redirigiendo al login...
              </p>
 
              <Link
                to="/login"
                className="mt-8 px-8 py-3 border border-secondary text-secondary hover:bg-secondary/10 rounded-full font-semibold text-sm transition-all active:scale-[0.98]"
              >
                Ir al login ahora
              </Link>
            </div>
          )}
 
          {/* ── Estado: token inválido ───────────────────────────────────────── */}
          {uiState === "invalid" && (
            <div className={`${cardClass} flex flex-col items-center text-center py-8`}>
              <div className="w-16 h-16 rounded-full flex items-center justify-center mb-6"
                style={{
                  background: "rgba(255,180,171,0.1)",
                  border: "1px solid rgba(255,180,171,0.2)",
                }}
              >
                <span className="material-symbols-outlined text-error text-[32px]">
                  link_off
                </span>
              </div>
 
              <h2 className="font-['Poppins'] text-2xl font-semibold text-on-surface mb-3">
                Enlace inválido
              </h2>
              <p className="text-sm text-on-surface-variant mb-8">
                Este enlace ha expirado o ya fue utilizado. Solicita uno nuevo.
              </p>
 
              <Link
                to="/forgot-password"
                className="w-full bg-primary-container hover:bg-primary text-on-primary font-semibold text-sm py-4 rounded-full transition-all active:scale-[0.98] text-center block"
              >
                Solicitar nuevo enlace
              </Link>
 
              <Link
                to="/login"
                className="mt-4 inline-flex items-center gap-2 text-[12px] font-medium text-on-surface-variant hover:text-secondary transition-colors group"
              >
                <span className="material-symbols-outlined text-[18px] group-hover:-translate-x-1 transition-transform">
                  arrow_back
                </span>
                Volver al login
              </Link>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
 
export default ResetPasswordPage;
