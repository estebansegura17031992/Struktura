/**
 * DangerZoneSection — Zona de peligro.
 * Botón "Eliminar cuenta" deshabilitado en MVP con tooltip.
 * Borde error/20, fondo error-container/5.
 */
const DangerZoneSection = () => (
  <section
    className="rounded-xl p-8"
    style={{
      background: "rgba(147,0,10,0.05)",
      backdropFilter: "blur(12px)",
      border: "1px solid rgba(255,180,171,0.2)",
    }}
  >
    <h2 className="font-['Poppins'] text-xl font-semibold text-error mb-4 flex items-center gap-2">
      <span className="material-symbols-outlined">warning</span>
      Zona de peligro
    </h2>
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
      <p className="text-base text-on-surface-variant max-w-xl">
        Eliminar tu cuenta es una acción permanente. Todos tus proyectos, tareas y datos asociados serán borrados de forma irreversible.
      </p>
      <div className="relative group">
        <button
          disabled
          className="px-8 py-3 rounded-full text-sm font-semibold cursor-not-allowed border border-outline-variant grayscale"
          style={{ background: "#333538", color: "rgba(220,193,178,0.5)" }}
        >
          Eliminar cuenta
        </button>
        <div className="absolute -top-12 left-1/2 -translate-x-1/2 hidden group-hover:block bg-surface-bright text-on-surface text-xs p-2 rounded shadow-xl z-10 w-48 text-center border border-outline-variant whitespace-nowrap">
          No disponible en esta versión
        </div>
      </div>
    </div>
  </section>
);
 
export default DangerZoneSection;
