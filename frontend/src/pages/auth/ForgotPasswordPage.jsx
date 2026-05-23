/**
 * ForgotPasswordPage — Recuperación de contraseña (R-0105).
 *
 * Un solo componente con DOS estados animados (fade + scale):
 *   Estado 1 "form"    → formulario con email + botón "Enviar instrucciones"
 *   Estado 2 "success" → confirmación con ícono cyan + ripple + botón "Entendido"
 *
 * Fiel al mockup Struktura:
 *  - Sin header ni footer — card centrada en viewport
 *  - Fondo gradiente radial dual: naranja top-right + cyan bottom-left
 *  - Card: surface-container-low, backdrop-blur, rounded-xl
 *  - Ícono lock_reset naranja en círculo con borde primary/20
 *  - Input email con ícono mail izquierdo y glow cyan al enfocar
 *  - Botón primary-container → hover primary, pill-shape
 *  - Estado éxito: mark_email_read con ripple animate-ping
 *  - Banner de rate limit oculto por defecto (animate-pulse)
 *  - R-0105: siempre retorna 200 — no revela si el email existe
 */
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { forgotPassword } from "@/api/auth";
 
// ─── Helpers ──────────────────────────────────────────────────────────────────
const isRateLimitError = (err) => err?.response?.status === 429;
 
// ─── Componente principal ─────────────────────────────────────────────────────
const ForgotPasswordPage = () => {
  // "form" | "success"
  const [uiState, setUiState]       = useState("form");
  const [transitioning, setTrans]   = useState(false);
  const [showRateLimit, setRateLimit] = useState(false);
  const [isSubmitting, setSubmitting] = useState(false);
 
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm();
 
  // ── Transición animada entre estados ────────────────────────────────────────
  const transitionTo = (next) => {
    setTrans(true);
    setTimeout(() => {
      setUiState(next);
      setTrans(false);
    }, 300);
  };
 
  // ── Submit ──────────────────────────────────────────────────────────────────
  const onSubmit = async (data) => {
    setSubmitting(true);
    setRateLimit(false);
    try {
      await forgotPassword(data.email.trim().toLowerCase());
      // R-0105: siempre mostrar éxito — no revelar si el email existe
      transitionTo("success");
    } catch (err) {
      if (isRateLimitError(err)) {
        setRateLimit(true);
      } else {
        // Cualquier otro error también muestra éxito (no revelar existencia de cuenta)
        transitionTo("success");
      }
    } finally {
      setSubmitting(false);
    }
  };
 
  // ── Volver al formulario desde éxito ────────────────────────────────────────
  const handleUnderstood = () => {
    reset();
    transitionTo("form");
  };
 
  // ── Clases de transición ─────────────────────────────────────────────────────
  const cardContentClass = `transition-all duration-300 ${
    transitioning ? "opacity-0 scale-95" : "opacity-100 scale-100"
  }`;
 
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
      <main className="w-full max-w-[400px] relative">
 
        {/* ── Banner rate limiting ─────────────────────────────────────────── */}
        {showRateLimit && (
          <div className="mb-4 bg-error-container/20 border border-error/30 p-4 rounded-lg flex items-start gap-3 animate-pulse">
            <span className="material-symbols-outlined text-error text-[20px] flex-shrink-0">
              report
            </span>
            <p className="text-sm font-semibold text-error">
              Por seguridad, intenta nuevamente en 5 minutos
            </p>
          </div>
        )}
 
        {/* ── Card principal ───────────────────────────────────────────────── */}
        <div
          className="border border-outline-variant/30 rounded-xl p-8 shadow-2xl relative overflow-hidden"
          style={{
            background: "rgba(28,31,34,0.7)",
            backdropFilter: "blur(12px)",
          }}
        >
          {/* ── Estado: formulario ──────────────────────────────────────────── */}
          {uiState === "form" && (
            <div className={cardContentClass}>
              <div className="flex flex-col items-center text-center">
 
                {/* Ícono lock_reset */}
                <div className="w-16 h-16 rounded-full flex items-center justify-center mb-8"
                  style={{
                    background: "rgba(218,119,38,0.1)",
                    border: "1px solid rgba(255,183,134,0.2)",
                  }}
                >
                  <span className="material-symbols-outlined text-primary text-[32px]">
                    lock_reset
                  </span>
                </div>
 
                <h1 className="font-['Poppins'] text-2xl font-semibold text-on-surface mb-2">
                  ¿Olvidaste tu contraseña?
                </h1>
                <p className="text-sm text-on-surface-variant mb-8">
                  Ingresa tu email y te enviaremos instrucciones para restablecerla.
                </p>
              </div>
 
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
 
                {/* Campo email con glow cyan */}
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider block">
                    Email
                  </label>
                  <div
                    className="relative group rounded-lg"
                    style={{ transition: "box-shadow 0.2s ease" }}
                  >
                    {/* Glow on focus-within */}
                    <style>{`
                      .email-wrap:focus-within {
                        box-shadow: 0 0 12px 2px rgba(37,191,217,0.2);
                      }
                    `}</style>
                    <div className="email-wrap relative rounded-lg">
                      <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant group-focus-within:text-secondary transition-colors text-[20px]">
                        mail
                      </span>
                      <input
                        type="email"
                        autoComplete="email"
                        placeholder="tu@email.com"
                        className={`w-full bg-surface-container-high border rounded-lg py-3 pl-12 pr-4 text-sm text-on-surface placeholder:text-on-surface-variant/30 focus:outline-none focus:border-secondary transition-all ${
                          errors.email ? "border-error/60" : "border-outline-variant/50"
                        }`}
                        {...register("email", {
                          required: "El email es requerido",
                          pattern: {
                            value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                            message: "Formato de email inválido",
                          },
                        })}
                      />
                    </div>
                  </div>
                  {errors.email && (
                    <p className="text-[11px] text-error ml-1 mt-0.5">
                      {errors.email.message}
                    </p>
                  )}
                </div>
 
                {/* Botón enviar — primary-container → hover primary */}
                <button
                  type="submit"
                  disabled={isSubmitting || showRateLimit}
                  className="w-full bg-primary-container hover:bg-primary text-on-primary font-semibold text-sm py-4 rounded-full transition-all active:scale-[0.98] shadow-lg shadow-primary/10 mt-4 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:bg-primary-container disabled:active:scale-100 flex items-center justify-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-4 h-4 rounded-full border-2 border-on-primary/30 border-t-on-primary animate-spin flex-shrink-0" />
                      <span>Procesando...</span>
                    </>
                  ) : (
                    "Enviar instrucciones"
                  )}
                </button>
              </form>
 
              {/* Link volver al login */}
              <div className="mt-8 text-center">
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
            <div className={`${cardContentClass} flex flex-col items-center text-center py-8`}>
 
              {/* Ícono mark_email_read con ripple */}
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
                  mark_email_read
                </span>
                {/* Ripple decorativo */}
                <div className="absolute inset-0 rounded-full border border-secondary/40 animate-ping opacity-20" />
              </div>
 
              <h2 className="font-['Poppins'] text-2xl font-semibold text-on-surface mb-3">
                ¡Correo enviado!
              </h2>
              <p className="text-base text-on-surface-variant">
                Si el email está registrado, recibirás las instrucciones en unos minutos.
              </p>
 
              {/* Botón Entendido — outline cyan */}
              <button
                onClick={handleUnderstood}
                className="mt-8 px-8 py-3 border border-secondary text-secondary hover:bg-secondary/10 rounded-full font-semibold text-sm transition-all active:scale-[0.98]"
              >
                Entendido
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
 
export default ForgotPasswordPage;
