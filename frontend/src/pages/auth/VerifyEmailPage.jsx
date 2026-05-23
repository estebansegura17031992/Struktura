/**
 * VerifyEmailPage — Verificación de email con OTP de 6 dígitos (R-0101).
 *
 * Fiel al mockup Struktura:
 *  - Header: solo logo centrado
 *  - Fondo: gradiente radial triple (naranja + cyan + marrón)
 *  - Ornamento: flecha trending_flat rotada 45° esquina sup-der, opacidad 10%
 *  - Ícono mark_email_unread animado con float-up
 *  - 6 inputs OTP individuales con glow cyan al enfocar
 *  - Auto-avance al escribir, auto-retroceso al borrar
 *  - Paste: distribuye automáticamente los 6 dígitos
 *  - Countdown expiración (24h desde el envío) con barra de progreso
 *  - Contador regresivo en botón Reenviar (60s)
 *  - Banner de error con animación shake + intentos restantes
 *  - Overlay de éxito fullscreen antes de redirigir
 *
 * Recibe el email desde:
 *   1. location.state.email (viene de RegisterPage / LoginPage)
 *   2. query param ?email=... (fallback)
 */
import { useState, useEffect, useRef, useCallback } from "react";
import { useLocation, useNavigate, useSearchParams, Link } from "react-router-dom";
import { verifyEmail, resendVerification } from "@/api/auth";
 
// ─── Constantes ───────────────────────────────────────────────────────────────
const OTP_LENGTH        = 6;
const RESEND_COOLDOWN   = 60;      // segundos
const MAX_ATTEMPTS      = 5;
const EXPIRY_SECONDS    = 24 * 60 * 60; // 24 horas en segundos
 
// ─── Helpers ──────────────────────────────────────────────────────────────────
const formatTime = (totalSeconds) => {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
};
 
const extractApiError = (err) => {
  const code = err?.response?.data?.error?.code;
  if (code === "TOKEN_INVALID")   return "Código incorrecto.";
  if (code === "TOKEN_EXPIRED")   return "El código ha expirado. Solicita uno nuevo.";
  if (code === "MAX_VERIFICATION_ATTEMPTS") return "Demasiados intentos. Solicita un nuevo código.";
  return err?.response?.data?.error?.message || "Error al verificar. Intenta de nuevo.";
};
 
// ─── Overlay de éxito ─────────────────────────────────────────────────────────
const SuccessOverlay = () => (
  <div className="fixed inset-0 z-[100] flex items-center justify-center"
    style={{ background: "rgba(17,19,22,0.95)", backdropFilter: "blur(16px)" }}>
    <div className="text-center" style={{ animation: "floatUp 1.2s cubic-bezier(0.22,1,0.36,1) forwards" }}>
      <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-8"
        style={{ background: "rgba(76,215,242,0.2)" }}>
        <span className="material-symbols-outlined text-secondary"
          style={{ fontSize: "64px", fontVariationSettings: "'FILL' 1" }}>
          check_circle
        </span>
      </div>
      <h2 className="font-['Poppins'] text-3xl font-semibold text-on-surface mb-3">
        ¡Verificación Exitosa!
      </h2>
      <p className="text-base text-on-surface-variant">
        Redirigiendo a tu panel de control...
      </p>
    </div>
  </div>
);
 
// ─── Componente principal ─────────────────────────────────────────────────────
const VerifyEmailPage = () => {
  const location     = useLocation();
  const navigate     = useNavigate();
  const [searchParams] = useSearchParams();
 
  // Email desde state del router o query param
  const email = location.state?.email || searchParams.get("email") || "";
 
  // Estado OTP
  const [digits, setDigits]           = useState(Array(OTP_LENGTH).fill(""));
  const inputRefs                     = useRef([]);
 
  // Estado UI
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg]         = useState("");
  const [attemptsLeft, setAttemptsLeft] = useState(MAX_ATTEMPTS);
  const [shake, setShake]               = useState(false);
  const [showSuccess, setShowSuccess]   = useState(false);
 
  // Cooldown reenvío
  const [resendCooldown, setResendCooldown] = useState(RESEND_COOLDOWN);
  const [canResend, setCanResend]           = useState(false);
  const [resending, setResending]           = useState(false);
  const [resentOk, setResentOk]             = useState(false);
 
  // Countdown expiración (24h)
  const [expirySeconds, setExpirySeconds] = useState(EXPIRY_SECONDS);
 
  // ── Timers ─────────────────────────────────────────────────────────────────
 
  // Countdown reenvío
  useEffect(() => {
    if (canResend) return;
    if (resendCooldown <= 0) { setCanResend(true); return; }
    const t = setTimeout(() => setResendCooldown((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCooldown, canResend]);
 
  // Countdown expiración
  useEffect(() => {
    if (expirySeconds <= 0) return;
    const t = setTimeout(() => setExpirySeconds((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [expirySeconds]);
 
  // Progreso de expiración (0 a 1, decrece)
  const expiryProgress = expirySeconds / EXPIRY_SECONDS;
 
  // ── Manejo OTP ─────────────────────────────────────────────────────────────
 
  const triggerShake = () => {
    setShake(true);
    setTimeout(() => setShake(false), 600);
  };
 
  const handleKeyDown = (e, index) => {
    if (e.key === "Backspace") {
      if (digits[index]) {
        // Borrar dígito actual
        const next = [...digits];
        next[index] = "";
        setDigits(next);
      } else if (index > 0) {
        // Retroceder al campo anterior
        inputRefs.current[index - 1]?.focus();
      }
    } else if (e.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < OTP_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };
 
  const handleChange = (e, index) => {
    const val = e.target.value.replace(/\D/g, ""); // solo dígitos
    if (!val) return;
 
    const next = [...digits];
    next[index] = val.slice(-1); // solo el último carácter
    setDigits(next);
    setErrorMsg("");
 
    // Auto-avance al siguiente campo
    if (index < OTP_LENGTH - 1) {
      inputRefs.current[index + 1]?.focus();
    } else {
      // Último campo — intentar verificar automáticamente
      inputRefs.current[index]?.blur();
    }
  };
 
  // Pegado: distribuye los 6 dígitos
  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, OTP_LENGTH);
    if (!pasted) return;
    const next = Array(OTP_LENGTH).fill("");
    pasted.split("").forEach((d, i) => { next[i] = d; });
    setDigits(next);
    setErrorMsg("");
    // Enfocar el último campo rellenado
    const lastIndex = Math.min(pasted.length, OTP_LENGTH - 1);
    inputRefs.current[lastIndex]?.focus();
  };
 
  // ── Submit ─────────────────────────────────────────────────────────────────
 
  const handleSubmit = useCallback(async (e) => {
    e?.preventDefault();
    const code = digits.join("");
    if (code.length < OTP_LENGTH) return;
    if (isSubmitting) return;
 
    setIsSubmitting(true);
    setErrorMsg("");
 
    try {
      await verifyEmail(email, code);
      setShowSuccess(true);
      // Redirigir a login tras 2s mostrando el overlay de éxito
      setTimeout(() => {
        navigate("/login", {
          state: { email, verified: true },
          replace: true,
        });
      }, 2000);
    } catch (err) {
      const msg = extractApiError(err);
      const newAttempts = Math.max(attemptsLeft - 1, 0);
      setAttemptsLeft(newAttempts);
      setErrorMsg(
        newAttempts > 0
          ? `${msg} ${newAttempts} intento${newAttempts !== 1 ? "s" : ""} restante${newAttempts !== 1 ? "s" : ""}.`
          : msg
      );
      triggerShake();
      // Limpiar los dígitos para reintentar
      setDigits(Array(OTP_LENGTH).fill(""));
      setTimeout(() => inputRefs.current[0]?.focus(), 100);
    } finally {
      setIsSubmitting(false);
    }
  }, [digits, email, isSubmitting, attemptsLeft, navigate]);
 
  // Auto-submit cuando todos los campos están llenos
  useEffect(() => {
    if (digits.every((d) => d !== "") && !isSubmitting && !showSuccess) {
      handleSubmit();
    }
  }, [digits]);
 
  // ── Reenviar ───────────────────────────────────────────────────────────────
 
  const handleResend = async () => {
    if (!canResend || resending) return;
    setResending(true);
    setResentOk(false);
    try {
      await resendVerification(email);
      setResentOk(true);
      setAttemptsLeft(MAX_ATTEMPTS);
      setErrorMsg("");
      setExpirySeconds(EXPIRY_SECONDS);
    } catch {
      // Siempre 200 del backend
      setResentOk(true);
    } finally {
      setResending(false);
      setCanResend(false);
      setResendCooldown(RESEND_COOLDOWN);
    }
  };
 
  // ── Render ─────────────────────────────────────────────────────────────────
 
  return (
    <>
      <style>{`
        @keyframes floatUp {
          0%   { transform: translateY(10px); opacity: 0; }
          100% { transform: translateY(0);    opacity: 1; }
        }
        .animate-float-up { animation: floatUp 1.2s cubic-bezier(0.22,1,0.36,1) forwards; }
        @keyframes shake {
          10%, 90% { transform: translate3d(-1px, 0, 0); }
          20%, 80% { transform: translate3d(2px, 0, 0); }
          30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
          40%, 60% { transform: translate3d(4px, 0, 0); }
        }
        .shake { animation: shake 0.5s cubic-bezier(.36,.07,.19,.97) both; }
        .otp-field:focus {
          box-shadow: 0 0 0 4px rgba(37,191,217,0.2);
          border-color: #4cd7f2 !important;
          outline: none;
        }
      `}</style>
 
      {/* Overlay de éxito */}
      {showSuccess && <SuccessOverlay />}
 
      <div
        className="min-h-screen flex flex-col items-center justify-between text-on-surface font-['Inter'] overflow-x-hidden"
        style={{
          background:
            "radial-gradient(circle at 10% 20%, rgba(217,118,37,0.15) 0%, transparent 40%), " +
            "radial-gradient(circle at 90% 80%, rgba(37,191,217,0.15) 0%, transparent 40%), " +
            "radial-gradient(circle at 50% 50%, rgba(153,104,64,0.1) 0%, transparent 60%), " +
            "#111316",
        }}
      >
        {/* ── Header — solo logo centrado ──────────────────────────────────── */}
        <header className="w-full h-20 flex items-center justify-center pt-8">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-container flex items-center justify-center rounded-full">
              <span
                className="material-symbols-outlined text-on-primary-container text-[18px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                hexagon
              </span>
            </div>
            <span className="font-['Poppins'] text-xl font-bold text-on-background">
              Struktura
            </span>
          </div>
        </header>
 
        {/* ── Main ─────────────────────────────────────────────────────────── */}
        <main className="flex-grow flex items-center justify-center w-full px-4 md:px-12 py-12">
          <div className="max-w-md w-full bg-surface-container border border-outline-variant/30 rounded-xl p-8 shadow-2xl relative overflow-hidden">
 
            {/* Ornamento decorativo — flecha rotada, esquina superior derecha */}
            <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
              <span
                className="material-symbols-outlined text-secondary"
                style={{ fontSize: "120px", transform: "rotate(45deg)", display: "block" }}
              >
                trending_flat
              </span>
            </div>
 
            <div className="flex flex-col items-center text-center relative z-10">
 
              {/* Ícono animado */}
              <div
                className="w-24 h-24 rounded-full flex items-center justify-center mb-8 animate-float-up"
                style={{ background: "rgba(218,119,38,0.2)" }}
              >
                <span
                  className="material-symbols-outlined text-primary"
                  style={{ fontSize: "48px", fontVariationSettings: "'FILL' 1" }}
                >
                  mark_email_unread
                </span>
              </div>
 
              <h1 className="font-['Poppins'] text-2xl font-semibold text-on-surface mb-2">
                Revisa tu email
              </h1>
              <p className="text-base text-on-surface-variant mb-8">
                Enviamos un código de 6 dígitos a{" "}
                <span className="text-on-surface font-semibold">
                  {email || "tu correo"}
                </span>
              </p>
 
              {/* Mensaje de reenvío exitoso */}
              {resentOk && (
                <div className="w-full mb-4 flex items-center gap-2 bg-secondary/10 border border-secondary/30 rounded-lg px-4 py-3">
                  <span className="material-symbols-outlined text-secondary text-[18px] flex-shrink-0">
                    check_circle
                  </span>
                  <p className="text-sm text-secondary">
                    Nuevo código enviado. Revisa tu bandeja.
                  </p>
                </div>
              )}
 
              <form onSubmit={handleSubmit} className="w-full space-y-6">
 
                {/* ── Grid OTP — 6 inputs individuales ────────────────────── */}
                <div
                  className={`flex justify-between gap-2 md:gap-3 ${shake ? "shake" : ""}`}
                  onPaste={handlePaste}
                >
                  {digits.map((digit, i) => (
                    <input
                      key={i}
                      ref={(el) => (inputRefs.current[i] = el)}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      placeholder="•"
                      value={digit}
                      autoFocus={i === 0}
                      className={`otp-field w-12 h-14 md:w-14 md:h-16 text-center text-2xl font-bold bg-surface-container-high border rounded-lg transition-all duration-200 text-on-surface placeholder:text-on-surface-variant/30 ${
                        errorMsg
                          ? "border-error/60"
                          : "border-outline-variant/50"
                      }`}
                      onChange={(e) => handleChange(e, i)}
                      onKeyDown={(e) => handleKeyDown(e, i)}
                    />
                  ))}
                </div>
 
                {/* ── Countdown de expiración ──────────────────────────────── */}
                <div className="flex flex-col items-center gap-2">
                  <div className="flex items-center gap-2 text-xs font-medium text-on-surface-variant">
                    <span className="material-symbols-outlined text-[18px]">schedule</span>
                    <span>
                      Expira en{" "}
                      <span className="text-secondary font-mono font-bold">
                        {formatTime(expirySeconds)}
                      </span>
                    </span>
                  </div>
                  {/* Barra de progreso — decrece con el tiempo */}
                  <div className="w-full bg-surface-container-highest h-1 rounded-full overflow-hidden">
                    <div
                      className="bg-secondary h-full rounded-full transition-all duration-500"
                      style={{ width: `${expiryProgress * 100}%` }}
                    />
                  </div>
                </div>
 
                {/* ── Banner de error con shake ────────────────────────────── */}
                {errorMsg && (
                  <div className="flex items-center justify-center gap-2 px-4 py-3 bg-error/10 border border-error/20 rounded-lg">
                    <span className="material-symbols-outlined text-error text-[18px] flex-shrink-0">
                      error
                    </span>
                    <span className="text-xs font-medium text-error">{errorMsg}</span>
                  </div>
                )}
 
                {/* ── Acciones ─────────────────────────────────────────────── */}
                <div className="space-y-4 pt-2">
 
                  {/* Botón Verificar — primary naranja */}
                  <button
                    type="submit"
                    disabled={digits.some((d) => !d) || isSubmitting || attemptsLeft === 0}
                    className="w-full h-14 bg-primary text-on-primary font-semibold text-sm rounded-full flex items-center justify-center gap-2 hover:bg-primary-container hover:text-on-primary-container active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
                  >
                    {isSubmitting ? (
                      <>
                        <div className="w-4 h-4 rounded-full border-2 border-on-primary/30 border-t-on-primary animate-spin flex-shrink-0" />
                        <span>Verificando...</span>
                      </>
                    ) : (
                      <>
                        <span>Verificar</span>
                        <span className="material-symbols-outlined text-[20px]">
                          arrow_forward
                        </span>
                      </>
                    )}
                  </button>
 
                  {/* Botón Reenviar con countdown */}
                  <div className="text-center">
                    <button
                      type="button"
                      onClick={handleResend}
                      disabled={!canResend || resending || attemptsLeft === 0}
                      className="text-xs font-medium text-on-surface-variant hover:text-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {resending
                        ? "Enviando..."
                        : canResend
                        ? "Reenviar código"
                        : `Reenviar código (${resendCooldown}s)`}
                    </button>
                  </div>
 
                  {/* Link volver al login */}
                  <div className="text-center pt-1">
                    <Link
                      to="/login"
                      className="text-xs text-on-surface-variant hover:text-secondary transition-colors inline-flex items-center gap-1"
                    >
                      <span className="material-symbols-outlined text-[14px]">
                        arrow_back
                      </span>
                      Volver al inicio de sesión
                    </Link>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </main>
 
        {/* ── Footer ───────────────────────────────────────────────────────── */}
        <footer
          className="w-full border-t border-outline-variant/10 backdrop-blur-sm"
          style={{ background: "rgba(12,14,17,0.5)" }}
        >
          <div className="max-w-7xl mx-auto px-6 md:px-12 py-4 flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-[12px] font-medium text-on-surface-variant">
              © 2024 Struktura Systems. All rights reserved.
            </p>
            <div className="flex items-center gap-8">
              {["Privacy Policy", "Support"].map((l) => (
                <a
                  key={l}
                  href="#"
                  className="text-[12px] font-medium text-on-surface-variant hover:text-secondary transition-colors"
                >
                  {l}
                </a>
              ))}
            </div>
          </div>
        </footer>
      </div>
    </>
  );
};
 
export default VerifyEmailPage;
