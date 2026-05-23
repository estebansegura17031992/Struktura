/**
 * SecuritySection — Sección "Seguridad" (R-0108).
 * Contraseña actual (full width) + grid 2 cols (nueva + confirmar).
 * StrengthMeter reutilizado del Register.
 * Label FORTALEZA: MEDIA-ALTA en cyan uppercase tracking-widest.
 * Advertencia "Al cambiar tu contraseña, se cerrarán todas tus sesiones activas."
 * Al éxito: clearAuth() + redirect /login (todas las sesiones revocadas).
 */
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { changePassword } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";
import StrengthMeter, { getPasswordScore } from "../ui/StrengthMeter";
 
const STRENGTH_LABELS = ["", "Muy débil", "Débil", "Fuerte", "Excelente"];
const STRENGTH_COLORS = ["", "#ffb4ab", "#da7726", "#f6ba8b", "#4cd7f2"];
 
const SecuritySection = () => {
  const navigate   = useNavigate();
  const { clearAuth } = useAuthStore();
 
  const [saving, setSaving]         = useState(false);
  const [newPassVal, setNewPassVal] = useState("");
  const [showCurrent, setShowCur]   = useState(false);
  const [showNew, setShowNew]       = useState(false);
  const [showConfirm, setShowConf]  = useState(false);
  const [apiError, setApiError]     = useState("");
 
  const score = getPasswordScore(newPassVal);
 
  const { register, handleSubmit, watch, formState: { errors }, reset } = useForm();
  const newPassword = watch("new_password", "");
 
  const onSubmit = async (data) => {
    setSaving(true);
    setApiError("");
    try {
      await changePassword(data.current_password, data.new_password);
      clearAuth();
      navigate("/login", { state: { passwordChanged: true } });
    } catch (err) {
      const code = err?.response?.data?.error?.code;
      const msg  = err?.response?.data?.error?.message;
      if (code === "INVALID_CREDENTIALS") {
        setApiError("La contraseña actual es incorrecta.");
      } else {
        setApiError(msg || "Error al actualizar la contraseña.");
      }
    } finally {
      setSaving(false);
    }
  };
 
  return (
    <section
      className="rounded-xl p-8 mb-6"
      style={{ background: "rgba(30,32,35,0.8)", backdropFilter: "blur(12px)", border: "1px solid #2D3135" }}
    >
      <h2 className="font-['Poppins'] text-xl font-semibold text-on-surface mb-6 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary text-[22px]">lock</span>
        Seguridad
      </h2>
 
      {apiError && (
        <div className="mb-4 flex items-center gap-2 bg-error/10 border border-error/30 rounded-lg px-4 py-3 text-sm text-error">
          <span className="material-symbols-outlined text-[18px] flex-shrink-0">error_outline</span>
          {apiError}
        </div>
      )}
 
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
 
        {/* Contraseña actual — ancho completo */}
        <div className="space-y-2">
          <label className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider block">
            Contraseña actual
          </label>
          <div className="relative">
            <input
              type={showCurrent ? "text" : "password"}
              autoComplete="current-password"
              placeholder="••••••••••••"
              className={`w-full bg-surface-container border rounded-xl px-4 py-3 pr-12 text-sm text-on-surface focus:border-secondary focus:outline-none transition-all ${
                errors.current_password ? "border-error/60" : "border-outline-variant"
              }`}
              {...register("current_password", { required: "La contraseña actual es requerida" })}
            />
            <button type="button" onClick={() => setShowCur(v => !v)}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface">
              <span className="material-symbols-outlined text-[20px]">
                {showCurrent ? "visibility_off" : "visibility"}
              </span>
            </button>
          </div>
          {errors.current_password && (
            <p className="text-[11px] text-error ml-1">{errors.current_password.message}</p>
          )}
        </div>
 
        {/* Grid 2 cols: Nueva + Confirmar */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
 
          {/* Nueva contraseña + StrengthMeter */}
          <div className="space-y-2">
            <label className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider block">
              Nueva contraseña
            </label>
            <div className="relative">
              <input
                type={showNew ? "text" : "password"}
                autoComplete="new-password"
                className={`w-full bg-surface-container border rounded-xl px-4 py-3 pr-12 text-sm text-on-surface focus:border-secondary focus:outline-none transition-all ${
                  errors.new_password ? "border-error/60" : "border-outline-variant"
                }`}
                {...register("new_password", {
                  required: "La nueva contraseña es requerida",
                  minLength: { value: 8, message: "Mínimo 8 caracteres" },
                  validate: (v) => /\d/.test(v) || "Debe contener al menos un número",
                  onChange: (e) => setNewPassVal(e.target.value),
                })}
              />
              <button type="button" onClick={() => setShowNew(v => !v)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface">
                <span className="material-symbols-outlined text-[20px]">
                  {showNew ? "visibility_off" : "visibility"}
                </span>
              </button>
            </div>
 
            {/* StrengthMeter — 4 barras estilo mockup */}
            {newPassVal && (
              <div className="pt-1">
                <div className="flex gap-1">
                  {[0, 1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-1 rounded-sm flex-1 transition-all duration-300"
                      style={{
                        backgroundColor: i < score ? STRENGTH_COLORS[score] : "#333538",
                      }}
                    />
                  ))}
                </div>
                {score > 0 && (
                  <p
                    className="text-[10px] font-bold uppercase tracking-widest mt-1"
                    style={{ color: STRENGTH_COLORS[score] }}
                  >
                    Fortaleza: {STRENGTH_LABELS[score]}
                  </p>
                )}
              </div>
            )}
            {errors.new_password && (
              <p className="text-[11px] text-error ml-1">{errors.new_password.message}</p>
            )}
          </div>
 
          {/* Confirmar contraseña */}
          <div className="space-y-2">
            <label className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider block">
              Confirmar contraseña
            </label>
            <div className="relative">
              <input
                type={showConfirm ? "text" : "password"}
                autoComplete="new-password"
                className={`w-full bg-surface-container border rounded-xl px-4 py-3 pr-12 text-sm text-on-surface focus:border-secondary focus:outline-none transition-all ${
                  errors.confirm_password ? "border-error/60" : "border-outline-variant"
                }`}
                {...register("confirm_password", {
                  required: "Confirma tu nueva contraseña",
                  validate: (v) => v === newPassword || "Las contraseñas no coinciden",
                })}
              />
              <button type="button" onClick={() => setShowConf(v => !v)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface">
                <span className="material-symbols-outlined text-[20px]">
                  {showConfirm ? "visibility_off" : "visibility"}
                </span>
              </button>
            </div>
            {errors.confirm_password && (
              <p className="text-[11px] text-error ml-1">{errors.confirm_password.message}</p>
            )}
          </div>
        </div>
 
        {/* Advertencia — todas las sesiones se cerrarán */}
        <div
          className="rounded-xl p-4 flex gap-3 items-center"
          style={{ background: "rgba(218,119,38,0.1)", border: "1px solid rgba(218,119,38,0.2)" }}
        >
          <span className="material-symbols-outlined text-primary flex-shrink-0">info</span>
          <p className="text-sm text-on-surface italic">
            Al cambiar tu contraseña, se cerrarán todas tus sesiones activas.
          </p>
        </div>
 
        {/* Botón */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="bg-primary-container text-on-primary px-8 py-3 rounded-full text-sm font-semibold hover:scale-[1.02] transition-transform active:scale-95 shadow-lg shadow-primary-container/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {saving ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-on-primary/30 border-t-on-primary animate-spin" />
                Actualizando...
              </>
            ) : (
              "Actualizar contraseña"
            )}
          </button>
        </div>
      </form>
    </section>
  );
};
 
export default SecuritySection;
