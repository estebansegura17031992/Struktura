/**
 * ProfilePage — Página de configuración de perfil (R-0108).
 *
 * Layout completo fiel al mockup Struktura:
 *  - Header sticky: Struktura bold naranja, nav, campana, avatar AM
 *  - Profile Header: avatar gradiente + chip rol + username monospace
 *  - Layout: sidebar (4 tabs) + contenido principal con scroll
 *  - Tab activo: fondo secondary, texto oscuro
 *  - 4 secciones: Información Personal, Seguridad, Sesiones, Zona de Peligro
 *  - Footer: surface-dim, 3 columnas
 *
 * Tabs sidebar:
 *  "perfil"        → PersonalInfoSection
 *  "seguridad"     → SecuritySection
 *  "sesiones"      → SessionsSection
 *  "notificaciones"→ placeholder (Sprint 5)
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { logoutUser } from "@/api/auth";
import ProfileHeader        from "@/components/profile/ProfileHeader";
import PersonalInfoSection  from "@/components/profile/PersonalInfoSection";
import SecuritySection      from "@/components/profile/SecuritySection";
import SessionsSection      from "@/components/profile/SessionsSection";
import DangerZoneSection    from "@/components/profile/DangerZoneSection";
 
// ─── Sidebar Nav ──────────────────────────────────────────────────────────────
const TABS = [
  { id: "perfil",         icon: "person",        label: "Perfil" },
  { id: "seguridad",      icon: "shield",        label: "Seguridad" },
  { id: "sesiones",       icon: "devices",       label: "Sesiones" },
  { id: "notificaciones", icon: "notifications", label: "Notificaciones" },
];
 
// ─── Componente principal ─────────────────────────────────────────────────────
const ProfilePage = () => {
  const { user, clearAuth }  = useAuthStore();
  const navigate             = useNavigate();
  const [activeTab, setActiveTab] = useState("perfil");
  const [userData, setUserData]   = useState(user);
 
  const handleLogout = async () => {
    try { await logoutUser(); } catch {}
    clearAuth();
    navigate("/login");
  };
 
  const initials = userData?.full_name
    ? userData.full_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : userData?.username?.slice(0, 2).toUpperCase() || "??";
 
  return (
    <div className="min-h-screen font-['Inter'] text-on-background" style={{ backgroundColor: "#111316" }}>
 
      {/* ── Header sticky ────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-outline-variant" style={{ backgroundColor: "#111316" }}>
        <div className="flex justify-between items-center w-full px-6 py-4 max-w-[1200px] mx-auto">
          <div className="flex items-center gap-8">
            <Link to="/dashboard" className="font-['Poppins'] text-2xl font-bold text-primary">
              Struktura
            </Link>
            <nav className="hidden md:flex gap-6">
              {["Dashboard", "Projects", "Tasks", "Team"].map((item) => (
                <a
                  key={item}
                  href="#"
                  className="text-base text-on-surface-variant hover:text-secondary transition-colors"
                >
                  {item}
                </a>
              ))}
            </nav>
          </div>
 
          <div className="flex items-center gap-4">
            <button className="text-on-surface-variant hover:text-secondary transition-colors" aria-label="Notificaciones">
              <span className="material-symbols-outlined">notifications</span>
            </button>
            {/* Avatar con dropdown implícito */}
            <button
              onClick={handleLogout}
              title="Cerrar sesión"
              className="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center text-on-primary-fixed font-bold text-xs hover:ring-2 hover:ring-secondary transition-all"
            >
              {initials}
            </button>
          </div>
        </div>
      </header>
 
      {/* ── Main ─────────────────────────────────────────────────────────── */}
      <main className="max-w-[1200px] mx-auto px-6 py-8">
 
        {/* Profile header — avatar grande */}
        <ProfileHeader user={userData} />
 
        {/* Layout 2 cols: sidebar + contenido */}
        <div className="flex flex-col md:flex-row gap-6">
 
          {/* Sidebar con tabs */}
          <aside
            className="w-full md:w-52 shrink-0 rounded-xl p-3 self-start sticky top-24"
            style={{ background: "rgba(30,32,35,0.8)", backdropFilter: "blur(12px)", border: "1px solid #2D3135" }}
          >
            <nav className="flex flex-col gap-1">
              {TABS.map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all text-left w-full ${
                      isActive
                        ? "text-on-secondary"
                        : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
                    }`}
                    style={isActive ? { backgroundColor: "#4cd7f2", color: "#00363f" } : {}}
                  >
                    <span className="material-symbols-outlined text-[20px]">{tab.icon}</span>
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </aside>
 
          {/* Contenido principal */}
          <div className="flex-1 min-w-0">
 
            {activeTab === "perfil" && (
              <PersonalInfoSection
                user={userData}
                onUpdated={(updated) => setUserData(updated)}
              />
            )}
 
            {activeTab === "seguridad" && <SecuritySection />}
 
            {activeTab === "sesiones" && <SessionsSection />}
 
            {activeTab === "notificaciones" && (
              <section
                className="rounded-xl p-8"
                style={{ background: "rgba(30,32,35,0.8)", backdropFilter: "blur(12px)", border: "1px solid #2D3135" }}
              >
                <h2 className="font-['Poppins'] text-xl font-semibold text-on-surface mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-[22px]">notifications</span>
                  Notificaciones
                </h2>
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <span className="material-symbols-outlined text-on-surface-variant text-[48px] mb-4 opacity-40">
                    construction
                  </span>
                  <p className="text-on-surface-variant text-sm">
                    Configuración de notificaciones disponible en Sprint 5.
                  </p>
                </div>
              </section>
            )}
 
            {/* Zona de peligro siempre visible al final */}
            {(activeTab === "perfil" || activeTab === "seguridad") && (
              <DangerZoneSection />
            )}
          </div>
        </div>
      </main>
 
      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer
        className="border-t border-outline-variant mt-12"
        style={{ backgroundColor: "#111316" }}
      >
        <div className="flex flex-col md:flex-row justify-between items-center w-full px-6 py-6 max-w-[1200px] mx-auto gap-4">
          <span className="font-['Poppins'] text-base font-bold text-on-surface">Struktura</span>
          <p className="text-sm text-on-surface-variant">© 2024 Struktura Systems Inc.</p>
          <div className="flex gap-6">
            {["Privacy Policy", "Terms of Service", "Security"].map((l) => (
              <a key={l} href="#" className="text-sm text-on-surface-variant hover:text-secondary transition-colors">
                {l}
              </a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
};
 
export default ProfilePage;
