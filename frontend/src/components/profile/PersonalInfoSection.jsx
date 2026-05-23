/**
 * PersonalInfoSection — Sección "Información personal" (R-0108).
 * Grid 2 cols: Nombre + Timezone selector.
 * Email y Username: readonly con opacity, tooltip on hover.
 * Nota: "El email y el username no pueden modificarse en esta versión."
 * Botón "Guardar cambios" → PATCH /users/me.
 */
import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { updateMe } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";
import { TIMEZONES } from "@/lib/timezones";
 
const PersonalInfoSection = ({ user, onUpdated }) => {
  const { setAuth, accessToken } = useAuthStore();
  const [saving, setSaving]     = useState(false);
  const [toastMsg, setToastMsg] = useState("");
  const [toastType, setToastType] = useState("success");
 
  const { register, handleSubmit, formState: { errors, isDirty }, reset } = useForm({
    defaultValues: {
      full_name: user?.full_name || "",
      timezone:  user?.timezone  || "UTC",
    },
  });
 
  useEffect(() => {
    reset({ full_name: user?.full_name || "", timezone: user?.timezone || "UTC" });
  }, [user, reset]);
 
  const showToast = (msg, type = "success") => {
    setToastMsg(msg);
    setToastType(type);
    setTimeout(() => setToastMsg(""), 3000);
  };
 
  const onSubmit = async (data) => {
    setSaving(true);
    try {
      const updated = await updateMe({
        full_name: data.full_name.trim() || undefined,
        timezone:  data.timezone,
      });
      setAuth(accessToken, updated);
      onUpdated?.(updated);
      reset({ full_name: updated.full_name || "", timezone: updated.timezone });
      showToast("Perfil actualizado correctamente.");
    } catch (err) {
      const msg = err?.response?.data?.error?.message || "Error al guardar cambios.";
      showToast(msg, "error");
    } finally {
      setSaving(false);
    }
  };
 
  return (
    <section
      className="rounded-xl p-8 mb-6"
      style={{ background: "rgba(30,32,35,0.8)", backdropFilter: "blur(12px)", border: "1px solid #2D3135" }}
    >
      {/* Header de sección */}
      <h2 className="font-['Poppins'] text-xl font-semibold text-on-surface mb-6 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary text-[22px]">
          badge
        </span>
        Información personal
      </h2>
 
      {/* Toast */}
      {toastMsg && (
        <div
          className={`mb-4 flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium ${
            toastType === "success"
              ? "bg-secondary/10 border border-secondary/30 text-secondary"
              : "bg-error/10 border border-error/30 text-error"
          }`}
        >
          <span className="material-symbols-outlined text-[18px] flex-shrink-0">
            {toastType === "success" ? "check_circle" : "error_outline"}
          </span>
          {toastMsg}
        </div>
      )}
 
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
        {/* Fila 1: Nombre + Timezone */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
 
          {/* Nombre completo — editable */}
          <div className="space-y-2">
            <label className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider block">
              Nombre completo
            </label>
            <input
              type="text"
              className={`w-full bg-surface-container border rounded-xl px-4 py-3 text-sm text-on-surface focus:border-secondary focus:outline-none transition-all ${
                errors.full_name ? "border-error/60" : "border-outline-variant"
              }`}
              {...register("full_name")}
            />
            {errors.full_name && (
              <p className="text-[11px] text-error ml-1">{errors.full_name.message}</p>
            )}
          </div>
 
          {/* Timezone — selector IANA */}
          <div className="space-y-2">
            <label className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider block">
              Zona horaria
            </label>
            <div className="relative">
              <span
                className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-secondary text-[18px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                public
              </span>
              <select
                className="w-full bg-surface-container border border-outline-variant rounded-xl pl-10 pr-10 py-3 text-sm text-on-surface focus:border-secondary focus:outline-none transition-all appearance-none"
                {...register("timezone", { required: "La timezone es requerida" })}
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz.value} value={tz.value} className="bg-surface-container">
                    {tz.label}
                  </option>
                ))}
              </select>
              <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px] pointer-events-none">
                expand_more
              </span>
            </div>
          </div>
        </div>
 
        {/* Fila 2: Email + Username (ambos readonly) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
 
          {/* Email readonly */}
          <div className="space-y-2">
            <label className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider flex items-center gap-1">
              Email
              <span
                className="material-symbols-outlined text-[14px] cursor-help opacity-50"
                title="El email no puede modificarse en esta versión"
              >
                info
              </span>
            </label>
            <input
              type="email"
              readOnly
              value={user?.email || ""}
              className="w-full bg-surface-dim border border-outline-variant/30 rounded-xl px-4 py-3 text-sm text-on-surface-variant cursor-not-allowed opacity-70"
            />
          </div>
 
          {/* Username readonly con tooltip */}
          <div className="space-y-2 relative group">
            <label className="text-[11px] font-medium text-on-surface-variant uppercase tracking-wider flex items-center gap-1">
              Username
              <span
                className="material-symbols-outlined text-[14px] cursor-help opacity-50"
                title="El username no puede modificarse en esta versión"
              >
                info
              </span>
            </label>
            <input
              type="text"
              readOnly
              value={`@${user?.username || ""}`}
              className="w-full bg-surface-dim border border-outline-variant/30 rounded-xl px-4 py-3 text-sm text-on-surface-variant cursor-not-allowed opacity-70 font-['JetBrains_Mono',monospace]"
            />
            {/* Tooltip */}
            <div className="absolute -top-10 left-0 hidden group-hover:block bg-surface-bright text-on-surface text-xs p-2 rounded shadow-xl z-10 w-52 border border-outline-variant whitespace-nowrap">
              El username no puede modificarse en esta versión.
            </div>
          </div>
        </div>
 
        {/* Footer de sección: nota + botón */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center pt-4 border-t border-outline-variant/50 gap-4">
          <p className="text-sm text-on-surface-variant italic">
            <span className="text-primary font-bold">Nota:</span> El email y el username no pueden modificarse en esta versión.
          </p>
          <button
            type="submit"
            disabled={saving || !isDirty}
            className="bg-primary-container text-on-primary px-8 py-3 rounded-full text-sm font-semibold hover:scale-[1.02] transition-transform active:scale-95 shadow-lg shadow-primary-container/20 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 flex items-center gap-2"
          >
            {saving ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-on-primary/30 border-t-on-primary animate-spin" />
                Guardando...
              </>
            ) : (
              "Guardar cambios"
            )}
          </button>
        </div>
      </form>
    </section>
  );
};
 
export default PersonalInfoSection;
