/**
 * ProjectsPage.jsx
 * Pantalla: Listado de proyectos — vista grid y lista
 * Sprint 2 · E03 · R-0301 a R-0303
 *
 * Layout fiel a los wireframes:
 *  - Sidebar izquierdo (mismo patrón que AdminUsersPage)
 *  - Header sticky con búsqueda global y nav
 *  - Toggle grid/lista
 *  - Botón "Nuevo Proyecto" en sidebar y en toolbar
 *  - Tarjeta "Crear Proyecto" en vista grid (última posición)
 *  - Paginación estándar
 */
import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { logoutUser } from "@/api/auth";
import { useProjects } from "@/hooks/useProjects";
import {
  ProjectCard, ProjectRow,
  ProjectCardSkeleton, ProjectRowSkeleton,
  ProjectEmptyState, CreateProjectCard,
  ProjectFormModal, DeleteConfirmModal,
} from "@/components/projects/ProjectComponents";
import { Pagination } from "@/components/ui/DesignSystem";

// ── Sidebar nav ────────────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { icon: "dashboard",      label: "Dashboard",  path: "/dashboard" },
  { icon: "folder_managed", label: "Proyectos",  path: "/projects",  active: true },
  { icon: "assignment",     label: "Tareas",     path: "/tasks" },
  { icon: "group",          label: "Equipo",     path: "/team" },
  { icon: "admin_panel_settings", label: "Administración", path: "/admin/users" },
];

export default function ProjectsPage() {
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  const {
    projects, total, page, pageSize, totalPages,
    loading, error, search, setSearch, setPage,
    viewMode, setViewMode,
    refresh,
    // Crear
    showCreate, openCreate, closeCreate,
    creating, createError, submitCreate,
    // Editar
    editingProject, openEdit, closeEdit,
    updating, editError, submitEdit,
    // Eliminar
    deletingProject, openDelete, closeDelete,
    deleting, deleteError, blockingTasks, submitDelete,
  } = useProjects();

  const handleLogout = async () => {
    try { await logoutUser(); } catch {}
    clearAuth();
    navigate("/login");
  };

  const initials = user?.full_name
    ? user.full_name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2)
    : user?.username?.slice(0, 2).toUpperCase() || "??";

  const canCreate = ["editor", "admin"].includes(user?.role);

  return (
    <div className="min-h-screen font-['Inter'] text-on-background" style={{ backgroundColor: "#111316" }}>

      {/* ── Header sticky ─────────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-50 border-b"
        style={{ backgroundColor: "#111316", borderColor: "#2D3135" }}
      >
        <div className="flex items-center justify-between px-6 py-3 gap-4">
          {/* Logo */}
          <Link to="/dashboard" className="font-['Poppins'] text-2xl font-bold text-primary flex-shrink-0">
            Struktura
          </Link>

          {/* Búsqueda global */}
          <div className="relative flex-1 max-w-md group">
            <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">
              search
            </span>
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar proyectos por nombre..."
              className="w-full rounded-full py-2 pl-11 pr-4 text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none transition-all"
              style={{
                background: "#1a1c1f",
                border: "1px solid #2D3135",
              }}
              onFocus={e  => e.target.style.borderColor = "#4cd7f2"}
              onBlur={e   => e.target.style.borderColor = "#2D3135"}
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            )}
          </div>

          {/* Right nav */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <nav className="hidden md:flex items-center gap-1 mr-2">
              {["Dashboard", "Proyectos", "Tareas", "Equipo"].map(item => (
                <a key={item}
                  href="#"
                  className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                    item === "Proyectos"
                      ? "text-primary font-medium"
                      : "text-on-surface-variant hover:text-on-surface"
                  }`}
                >
                  {item}
                </a>
              ))}
            </nav>
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

      {/* ── Layout: sidebar + main ─────────────────────────────────────────── */}
      <div className="flex min-h-[calc(100vh-57px)]">

        {/* Sidebar */}
        <aside
          className="w-60 shrink-0 flex flex-col py-4 sticky top-[57px] h-[calc(100vh-57px)] overflow-y-auto"
          style={{ background: "#111316", borderRight: "1px solid #2D3135" }}
        >
          <nav className="flex flex-col gap-0.5 px-3 flex-1">
            {NAV_ITEMS.map(item => (
              <Link
                key={item.label}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  item.active
                    ? "text-on-surface"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
                }`}
                style={item.active ? { background: "rgba(255,183,134,0.12)" } : {}}
              >
                <span
                  className="material-symbols-outlined text-[20px]"
                  style={item.active ? { color: "#ffb786" } : {}}
                >
                  {item.icon}
                </span>
                {item.label}
              </Link>
            ))}
          </nav>

          {/* CTA Nuevo Proyecto en sidebar */}
          {canCreate && (
            <div className="px-3 pb-4 mt-auto">
              <button
                onClick={openCreate}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-full font-semibold text-sm transition-opacity hover:opacity-90"
                style={{ background: "#da7726", color: "#461f00" }}
              >
                <span className="material-symbols-outlined text-[18px]">add</span>
                Nuevo Proyecto
              </button>
            </div>
          )}
        </aside>

        {/* Main */}
        <main className="flex-1 flex flex-col overflow-hidden">

          {/* Top bar */}
          <div
            className="px-6 pt-6 pb-4 border-b"
            style={{ borderColor: "#2D3135" }}
          >
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-on-surface-variant mb-3">
              <span>Workspace</span>
              <span className="material-symbols-outlined text-[14px]">chevron_right</span>
              <span className="text-on-surface font-medium">Proyectos</span>
            </div>

            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <h1 className="font-['Poppins'] text-2xl font-bold text-on-surface">Proyectos</h1>
                {!loading && (
                  <span
                    className="px-3 py-0.5 rounded-full text-xs font-semibold text-on-surface-variant"
                    style={{ background: "#1e2023", border: "1px solid #2D3135" }}
                  >
                    {total} proyectos
                  </span>
                )}
              </div>

              <div className="flex items-center gap-3">
                {/* Toggle vista */}
                <div
                  className="flex rounded-xl overflow-hidden"
                  style={{ border: "1px solid #2D3135", background: "#1a1c1f" }}
                >
                  {[
                    { mode: "grid", icon: "grid_view" },
                    { mode: "list", icon: "view_list" },
                  ].map(v => (
                    <button
                      key={v.mode}
                      onClick={() => setViewMode(v.mode)}
                      className={`w-10 h-9 flex items-center justify-center transition-all ${
                        viewMode === v.mode
                          ? "text-primary-container"
                          : "text-on-surface-variant hover:text-on-surface"
                      }`}
                      style={viewMode === v.mode ? { background: "rgba(218,119,38,0.2)" } : {}}
                      aria-label={v.mode === "grid" ? "Vista grid" : "Vista lista"}
                    >
                      <span className="material-symbols-outlined text-[20px]">{v.icon}</span>
                    </button>
                  ))}
                </div>

                {/* CTA en toolbar */}
                {canCreate && (
                  <button
                    onClick={openCreate}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-full font-semibold text-sm transition-opacity hover:opacity-90"
                    style={{ background: "#da7726", color: "#461f00" }}
                  >
                    <span className="material-symbols-outlined text-[18px]">add</span>
                    Nuevo Proyecto
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="p-6 flex-1 overflow-x-hidden">

            {/* Error */}
            {error && (
              <div
                className="mb-6 px-5 py-4 rounded-xl flex items-center gap-3"
                style={{ background: "rgba(255,180,171,0.1)", border: "1px solid rgba(255,180,171,0.3)" }}
              >
                <span className="material-symbols-outlined text-error">error</span>
                <span className="text-error text-sm flex-1">{error}</span>
                <button onClick={refresh} className="text-error text-sm font-bold underline underline-offset-2">
                  Reintentar
                </button>
              </div>
            )}

            {/* ── Vista Grid ─────────────────────────────────────────────── */}
            {viewMode === "grid" && (
              <>
                {loading ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Array.from({ length: 6 }).map((_, i) => <ProjectCardSkeleton key={i} />)}
                  </div>
                ) : projects.length === 0 && !search ? (
                  <ProjectEmptyState onCreateClick={openCreate} />
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {projects.map(p => (
                      <ProjectCard key={p.id} project={p} onEdit={openEdit} onDelete={openDelete} />
                    ))}
                    {canCreate && (
                      <CreateProjectCard onClick={openCreate} />
                    )}
                  </div>
                )}
              </>
            )}

            {/* ── Vista Lista ─────────────────────────────────────────────── */}
            {viewMode === "list" && (
              <div
                className="rounded-xl overflow-hidden"
                style={{ background: "#1a1c1f", border: "1px solid #2D3135" }}
              >
                <table className="w-full text-left border-collapse" aria-label="Lista de proyectos">
                  <thead style={{ background: "#1e2023" }}>
                    <tr>
                      {["Proyecto", "Descripción", "Equipo", "Creado", "Acciones"].map(h => (
                        <th key={h} className="px-6 py-3 text-xs font-medium uppercase tracking-wider text-on-surface-variant whitespace-nowrap">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {loading
                      ? Array.from({ length: 5 }).map((_, i) => <ProjectRowSkeleton key={i} />)
                      : projects.map(p => (
                          <ProjectRow key={p.id} project={p} onEdit={openEdit} onDelete={openDelete} />
                        ))
                    }
                  </tbody>
                </table>
                {!loading && projects.length === 0 && (
                  <ProjectEmptyState onCreateClick={openCreate} />
                )}
              </div>
            )}

            {/* Paginación */}
            {!loading && total > pageSize && (
              <div className="mt-6">
                <Pagination
                  page={page}
                  totalPages={totalPages}
                  total={total}
                  pageSize={pageSize}
                  onPageChange={setPage}
                />
              </div>
            )}
          </div>
        </main>
      </div>

      {/* ── Modales ─────────────────────────────────────────────────────────── */}
      {showCreate && (
        <ProjectFormModal
          mode="create"
          loading={creating}
          error={createError}
          onSubmit={submitCreate}
          onClose={closeCreate}
        />
      )}

      {editingProject && (
        <ProjectFormModal
          mode="edit"
          project={editingProject}
          loading={updating}
          error={editError}
          onSubmit={submitEdit}
          onClose={closeEdit}
          onDelete={() => { closeEdit(); openDelete(editingProject); }}
        />
      )}

      {deletingProject && (
        <DeleteConfirmModal
          project={deletingProject}
          loading={deleting}
          error={deleteError}
          blockingTasks={blockingTasks}
          onConfirm={submitDelete}
          onClose={closeDelete}
        />
      )}
    </div>
  );
}