/**
 * AdminUsersPage.jsx
 * Panel Administración de Usuarios — Sprint 2 · E02 · R-0204
 * Layout fiel al mockup Struktura:
 *  - Header sticky: logo, campana, avatar
 *  - Sidebar izquierdo: nav principal + Administración expandido
 *  - Contenido: toolbar + tabla de usuarios
 */
import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { logoutUser } from "@/api/auth";
import { useAdminUsers } from "@/hooks/useAdminUsers";
import { UsersTable } from "@/components/ui/UsersTable";
import { ConfirmRoleModal } from "@/components/ui/ConfirmRoleModal";
import { Pagination, Spinner } from "@/components/ui/DesignSystem";

// ── Sidebar nav items (sin Administración — se muestra como bloque expandible abajo) ──
const NAV_ITEMS = [
  { icon: "dashboard",      label: "Dashboard", path: "/dashboard" },
  { icon: "folder_managed", label: "Proyectos", path: "/projects" },
  { icon: "assignment",     label: "Tareas",    path: "/tasks" },
  { icon: "group",          label: "Equipo",    path: "/team" },
];

const ADMIN_SUB = [
  { label: "Usuarios",      path: "/admin/users",  active: true  },
  { label: "Configuración", path: "/admin/config", active: false },
];

export default function AdminUsersPage() {
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();
  const [adminOpen, setAdminOpen] = useState(true);

  const {
    users, total, page, pageSize, totalPages,
    loading, error,
    search, setSearch,
    roleFilter, setRoleFilter,
    setPage,
    pendingRoleChange, requestRoleChange, confirmRoleChange, cancelRoleChange,
    roleChangeLoading, roleChangeError,
    refresh,
  } = useAdminUsers();

  const handleLogout = async () => {
    try { await logoutUser(); } catch {}
    clearAuth();
    navigate("/login");
  };

  const initials = user?.full_name
    ? user.full_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : user?.username?.slice(0, 2).toUpperCase() || "??";

  return (
    <div className="min-h-screen font-['Inter'] text-on-background" style={{ backgroundColor: "#111316" }}>

      {/* ── Header sticky ───────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-outline-variant" style={{ backgroundColor: "#111316" }}>
        <div className="flex justify-between items-center w-full px-6 py-4">
          <Link to="/dashboard" className="font-['Poppins'] text-2xl font-bold text-primary">
            Struktura
          </Link>
          <div className="flex items-center gap-4">
            <button className="text-on-surface-variant hover:text-secondary transition-colors" aria-label="Notificaciones">
              <span className="material-symbols-outlined">notifications</span>
            </button>
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

      {/* ── Layout: sidebar + contenido ─────────────────────────────────── */}
      <div className="flex min-h-[calc(100vh-65px)]">

        {/* Sidebar izquierdo */}
        <aside
          className="w-64 shrink-0 flex flex-col py-6 px-4 gap-1 sticky top-[65px] h-[calc(100vh-65px)] overflow-y-auto"
          style={{ background: "#111316", borderRight: "1px solid #2D3135" }}
        >
          {/* Nav principal */}
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.label}
              to={item.path}
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-all"
            >
              <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
              {item.label}
            </Link>
          ))}

          {/* Administración — expandible */}
          <div className="mt-1">
            <button
              onClick={() => setAdminOpen(v => !v)}
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium w-full text-left transition-all"
              style={{ backgroundColor: "#da7726", color: "#461f00" }}
            >
              <span
                className="material-symbols-outlined text-[20px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                admin_panel_settings
              </span>
              <span className="flex-1">Administración</span>
              <span className="material-symbols-outlined text-[18px]">
                {adminOpen ? "keyboard_arrow_down" : "keyboard_arrow_right"}
              </span>
            </button>

            {adminOpen && (
              <div className="ml-10 flex flex-col gap-0.5 mt-1">
                {ADMIN_SUB.map((sub) => (
                  <Link
                    key={sub.label}
                    to={sub.path}
                    className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                      sub.active
                        ? "text-primary"
                        : "text-on-surface-variant hover:text-on-surface"
                    }`}
                    style={sub.active ? { backgroundColor: "rgba(255,183,134,0.12)" } : {}}
                  >
                    {sub.label}
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Footer del sidebar */}
          <div className="mt-auto pt-6 border-t border-outline-variant/30 flex flex-col gap-1">
            <Link
              to="/settings"
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-all"
            >
              <span className="material-symbols-outlined text-[20px]">settings</span>
              Configuración
            </Link>
            <Link
              to="/help"
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-all"
            >
              <span className="material-symbols-outlined text-[20px]">help</span>
              Ayuda
            </Link>
          </div>
        </aside>

        {/* Contenido principal */}
        <main className="flex-1 flex flex-col overflow-hidden">

          {/* Top app bar */}
          <div
            className="sticky top-[65px] z-40 px-6 py-4 border-b border-outline-variant/30"
            style={{ backgroundColor: "#111316" }}
          >
            <h1 className="font-['Poppins'] text-2xl font-bold text-on-surface">
              Administración de Usuarios
            </h1>
          </div>

          <div className="p-6 flex-1 overflow-x-hidden">

            {/* Toolbar */}
            <section className="mb-6 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3 flex-1 min-w-[280px]">
                {/* Búsqueda */}
                <div className="relative flex-1 max-w-md group">
                  <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant group-focus-within:text-secondary transition-colors text-[20px]">
                    search
                  </span>
                  <input
                    type="text"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="Buscar por nombre o email..."
                    className="w-full bg-surface-container-low border border-outline-variant rounded-full py-2.5 pl-12 pr-4 text-sm focus:outline-none focus:border-secondary transition-all"
                  />
                  {search && (
                    <button
                      onClick={() => setSearch("")}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
                    >
                      <span className="material-symbols-outlined text-[18px]">close</span>
                    </button>
                  )}
                </div>

                {/* Filtro rol */}
                <div className="relative">
                  <select
                    value={roleFilter}
                    onChange={e => setRoleFilter(e.target.value)}
                    className="appearance-none bg-surface-container-low border border-outline-variant rounded-full py-2.5 pl-4 pr-10 text-sm focus:outline-none focus:border-secondary cursor-pointer"
                  >
                    <option value="">Todos los roles</option>
                    <option value="admin">Admin</option>
                    <option value="editor">Editor</option>
                    <option value="viewer">Viewer</option>
                  </select>
                  <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none text-[18px]">
                    expand_more
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-4">
                {loading ? (
                  <Spinner size={16} />
                ) : (
                  <span className="text-on-surface-variant text-sm">
                    <strong className="text-on-surface">{total}</strong> usuarios
                  </span>
                )}
                <button className="bg-primary-container text-on-primary-container hover:opacity-90 transition-opacity px-6 py-2.5 rounded-full text-sm flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px]">person_add</span>
                  Nuevo Usuario
                </button>
              </div>
            </section>

            {/* Error */}
            {error && (
              <div className="mb-6 px-5 py-4 bg-error-container/20 border border-error/30 rounded-xl text-error flex items-center gap-3">
                <span className="material-symbols-outlined flex-shrink-0">error</span>
                <span className="text-sm flex-1">{error}</span>
                <button onClick={refresh} className="text-sm font-bold underline underline-offset-2 hover:no-underline">
                  Reintentar
                </button>
              </div>
            )}

            {/* Tabla */}
            <UsersTable
              users={users}
              loading={loading}
              currentUserId={user?.id}
              onRequestRoleChange={requestRoleChange}
            />

            {/* Paginación */}
            {!loading && total > pageSize && (
              <Pagination
                page={page}
                totalPages={totalPages}
                total={total}
                pageSize={pageSize}
                onPageChange={setPage}
              />
            )}

            {/* Modal confirmación cambio de rol */}
            <ConfirmRoleModal
              pending={pendingRoleChange}
              loading={roleChangeLoading}
              error={roleChangeError}
              onConfirm={confirmRoleChange}
              onCancel={cancelRoleChange}
            />
          </div>
        </main>
      </div>
    </div>
  );
}