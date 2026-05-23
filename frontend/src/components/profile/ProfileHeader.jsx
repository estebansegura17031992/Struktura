/**
 * ProfileHeader — Cabecera del perfil con avatar, nombre, chip de rol y username.
 * Avatar: gradiente from-primary-container to-primary, ring exterior, iniciales font-black.
 * Botón edit cyan en esquina inferior derecha del avatar.
 * Chip Admin: fondo secondary-container/20, borde secondary-container/30.
 * Username: fuente monospace (JetBrains Mono).
 */
const ProfileHeader = ({ user }) => {
  const initials = user?.full_name
    ? user.full_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : user?.username?.slice(0, 2).toUpperCase() || "??";
 
  const roleLabel = user?.role === "admin" ? "Admin" : user?.role === "editor" ? "Editor" : "Viewer";
 
  return (
    <section className="mb-8">
      <div
        className="rounded-xl p-8 flex flex-col md:flex-row items-center gap-6"
        style={{ background: "rgba(30,32,35,0.8)", backdropFilter: "blur(12px)", border: "1px solid #2D3135" }}
      >
        {/* Avatar con gradiente */}
        <div className="relative group">
          <div
            className="w-32 h-32 rounded-full flex items-center justify-center text-4xl font-black text-on-primary shadow-xl"
            style={{
              background: "linear-gradient(to bottom right, #da7726, #ffb786)",
              boxShadow: "0 0 0 4px rgba(85,67,55,0.3)",
            }}
          >
            {initials}
          </div>
          <button
            className="absolute bottom-0 right-0 p-2 bg-secondary text-on-secondary rounded-full shadow-lg hover:scale-105 transition-transform"
            aria-label="Editar foto de perfil"
            title="Cambiar foto — no disponible en MVP"
            disabled
          >
            <span className="material-symbols-outlined text-sm">edit</span>
          </button>
        </div>
 
        {/* Datos del usuario */}
        <div className="text-center md:text-left flex-1">
          <div className="flex flex-col md:flex-row md:items-center gap-3 mb-1">
            <h1 className="font-['Poppins'] text-3xl font-semibold text-on-surface">
              {user?.full_name || user?.username || "Usuario"}
            </h1>
            <span
              className="px-3 py-0.5 rounded-full text-sm font-semibold self-center md:self-auto"
              style={{
                background: "rgba(0,179,205,0.2)",
                color: "#4cd7f2",
                border: "1px solid rgba(0,179,205,0.3)",
              }}
            >
              {roleLabel}
            </span>
          </div>
          <p className="font-['JetBrains_Mono',monospace] text-on-surface-variant text-base">
            @{user?.username || ""}
          </p>
        </div>
      </div>
    </section>
  );
};
 
export default ProfileHeader;
