/**
 * BoardPage.jsx
 * Pantalla: Tablero Kanban de un proyecto
 * Sprint 3 · E04 · R-0401, R-0403, R-0406, AG-03, DU-03
 *
 * Layout fiel al mockup aprobado (artefacto 10):
 *  - Mismo patrón de header + sidebar que ProjectsPage/ProjectMembersPage
 *  - 3 columnas siempre visibles (abierto / en_proceso / completo)
 *  - Barra de filtros: prioridad, asignado (viewer forzado a "me"), búsqueda FTS
 *  - Empty state por columna: CTA solo en "Abierto" sin filtro (AG-03),
 *    "Sin tareas con este filtro" cuando hay filtros activos (DU-03)
 *
 * Drag & drop (@dnd-kit/core, artefacto 11) se implementa en un pase
 * siguiente. Este pase cubre los mockups #1 (tablero), #2 (tarjeta) y #14
 * (modal de creación/edición) ya aprobados.
 */
import React, { useEffect } from "react";
import { Link, useNavigate, useParams, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { logoutUser } from "@/api/auth";
import { useTasks } from "@/hooks/useTasks";
import { useMembers } from "@/hooks/useMembers";
import { TaskCard, TaskCardSkeleton, EmptyColumn, TaskFormModal } from "@/components/tasks/TaskComponents";

// ── Sidebar nav ────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { icon: "dashboard",            label: "Dashboard",      path: "/dashboard" },
  { icon: "folder_managed",       label: "Proyectos",      path: "/projects" },
  { icon: "assignment",           label: "Tareas",         path: "/tasks",       active: true },
  { icon: "group",                label: "Equipo",         path: "/team" },
  { icon: "admin_panel_settings", label: "Administración", path: "/admin/users" },
];

const COLUMNS = [
  { status: "abierto",    label: "Abierto",    dot: "#ffb786" },
  { status: "en_proceso", label: "En proceso", dot: "#4cd7f2" },
  { status: "completo",   label: "Completo",   dot: "#4ade80" },
];

export default function BoardPage() {
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const { projectId } = useParams();

  // Nombre/rol del proyecto: viene del state de navegación (ProjectsPage ya
  // tiene el objeto completo). No existe GET /projects/{id} en el backend
  // todavía, así que evitamos depender de un endpoint que no existe.
  const projectFromState = location.state?.project ?? null;
  const projectName = projectFromState?.name ?? "Tablero";
  const myRole = projectFromState?.my_role ?? user?.role;
  const isViewer = myRole === "viewer";
  const canCreate = ["editor", "admin", "owner"].includes(myRole);

  const {
    columns, loading, error, refresh,
    priority, setPriority,
    assignedTo, setAssignedTo,
    search, setSearch,
    hasActiveFilters, clearFilters,
    // Crear
    showCreate, openCreateTask, closeCreateTask,
    creating, createError, submitCreateTask,
    // Editar
    editingTask, openEditTask, closeEditTask,
    updating, editError, submitEditTask,
    // Eliminar
    deleting, deleteError, submitDeleteTask,
  } = useTasks(projectId);

  // Miembros activos del proyecto — fuente del selector de asignados (solo
  // miembros activos pueden asignarse a tareas nuevas, R-0401).
  const { members } = useMembers(projectId);

  // Viewer solo puede filtrar assigned_to=me (R-0403) — se fuerza en cliente.
  useEffect(() => {
    if (isViewer && assignedTo !== "me") setAssignedTo("me");
  }, [isViewer, assignedTo, setAssignedTo]);

  const handleLogout = async () => {
    try { await logoutUser(); } catch {}
    clearAuth();
    navigate("/login");
  };

  const initials = user?.full_name
    ? user.full_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : user?.username?.slice(0, 2).toUpperCase() || "??";

  const totalTasks = COLUMNS.reduce((acc, c) => acc + (columns[c.status]?.length ?? 0), 0);

  return (
    <div className="min-h-screen font-['Inter'] text-on-background flex flex-col" style={{ backgroundColor: "#111316" }}>

      {/* ── Header sticky ─────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b" style={{ backgroundColor: "#111316", borderColor: "#2D3135" }}>
        <div className="flex items-center justify-between px-6 py-3 gap-4">
          <Link to="/dashboard" className="font-['Poppins'] text-2xl font-bold text-primary flex-shrink-0">
            Struktura
          </Link>
          <div className="flex items-center gap-2 flex-shrink-0 ml-auto">
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

      <div className="flex flex-1 min-h-[calc(100vh-57px)]">

        {/* Sidebar */}
        <aside
          className="w-60 shrink-0 flex flex-col py-4 sticky top-[57px] h-[calc(100vh-57px)] overflow-y-auto"
          style={{ background: "#111316", borderRight: "1px solid #2D3135" }}
        >
          <nav className="flex flex-col gap-0.5 px-3 flex-1">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.label}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  item.active ? "text-on-surface" : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container"
                }`}
                style={item.active ? { background: "rgba(255,183,134,0.12)" } : {}}
              >
                <span className="material-symbols-outlined text-[20px]" style={item.active ? { color: "#ffb786" } : {}}>
                  {item.icon}
                </span>
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>

        {/* Main */}
        <main className="flex-1 flex flex-col overflow-hidden">

          {/* Top bar */}
          <div className="px-6 pt-6 pb-4 border-b" style={{ borderColor: "#2D3135" }}>
            <div className="flex items-center gap-2 text-sm text-on-surface-variant mb-3">
              <Link to="/projects" className="hover:text-on-surface">Proyectos</Link>
              <span className="material-symbols-outlined text-[14px]">chevron_right</span>
              <span className="text-on-surface font-medium">{projectName}</span>
              <span className="material-symbols-outlined text-[14px]">chevron_right</span>
              <span className="text-primary">Tablero</span>
            </div>

            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <h1 className="font-['Poppins'] text-2xl font-bold text-on-surface">Tablero</h1>
                {!loading && (
                  <span
                    className="px-3 py-0.5 rounded-full text-xs font-semibold text-on-surface-variant"
                    style={{ background: "#1e2023", border: "1px solid #2D3135" }}
                  >
                    {totalTasks} tareas
                  </span>
                )}
              </div>

              {canCreate && (
                <button
                  onClick={openCreateTask}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-full font-semibold text-sm transition-opacity hover:opacity-90"
                  style={{ background: "#da7726", color: "#461f00" }}
                >
                  <span className="material-symbols-outlined text-[18px]">add</span>
                  Nueva tarea
                </button>
              )}
            </div>
          </div>

          {/* Filter bar */}
          <div className="px-6 py-3 border-b flex flex-wrap items-center gap-3" style={{ borderColor: "#2D3135" }}>
            <div className="relative">
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="appearance-none rounded-full pl-4 pr-9 py-2 text-sm text-on-surface focus:outline-none cursor-pointer"
                style={{ background: "#1a1c1f", border: "1px solid #2D3135" }}
              >
                <option value="">Prioridad</option>
                <option value="high">Alta</option>
                <option value="medium">Media</option>
                <option value="low">Baja</option>
              </select>
              <span className="material-symbols-outlined absolute right-2.5 top-1/2 -translate-y-1/2 text-on-surface-variant text-[16px] pointer-events-none">expand_more</span>
            </div>

            {!isViewer && (
              <div className="flex rounded-full overflow-hidden" style={{ border: "1px solid #2D3135", background: "#1a1c1f" }}>
                {[
                  { val: "", label: "Todos" },
                  { val: "me", label: "Yo" },
                ].map((o) => (
                  <button
                    key={o.val}
                    onClick={() => setAssignedTo(o.val)}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      assignedTo === o.val ? "text-primary-container" : "text-on-surface-variant hover:text-on-surface"
                    }`}
                    style={assignedTo === o.val ? { background: "rgba(218,119,38,0.2)" } : {}}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            )}

            <div className="relative flex-1 min-w-[200px] max-w-xs">
              <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">search</span>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar tarea… (mín. 2 caracteres)"
                className="w-full rounded-full py-2 pl-10 pr-4 text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none transition-all"
                style={{ background: "#1a1c1f", border: "1px solid #2D3135" }}
              />
            </div>

            {hasActiveFilters && (
              <button onClick={clearFilters} className="text-on-surface-variant text-sm hover:text-primary underline underline-offset-4">
                Limpiar filtros
              </button>
            )}
          </div>

          {/* Board */}
          <div className="flex-1 overflow-x-auto p-6">
            {error ? (
              <div
                className="px-5 py-4 rounded-xl flex items-center gap-3"
                style={{ background: "rgba(255,180,171,0.1)", border: "1px solid rgba(255,180,171,0.3)" }}
              >
                <span className="material-symbols-outlined text-error">error</span>
                <span className="text-error text-sm flex-1">{error}</span>
                <button onClick={refresh} className="text-error text-sm font-bold underline underline-offset-2">
                  Reintentar
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-full min-w-[900px] md:min-w-0">
                {COLUMNS.map((col) => {
                  const items = columns[col.status] ?? [];
                  return (
                    <div key={col.status} className="flex flex-col gap-4">
                      <div
                        className="flex justify-between items-center px-4 py-2 rounded-lg"
                        style={{ background: "#1e2023", border: "1px solid rgba(85,67,55,0.15)" }}
                      >
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full" style={{ background: col.dot }} />
                          <h2 className="text-xs font-bold tracking-wider text-on-surface uppercase">{col.label}</h2>
                        </div>
                        <span
                          className="px-2 py-0.5 rounded text-xs font-bold text-on-surface-variant"
                          style={{ background: "#333538" }}
                        >
                          {loading ? "…" : items.length}
                        </span>
                      </div>

                      <div className="flex flex-col gap-3 flex-1">
                        {loading ? (
                          Array.from({ length: 2 }).map((_, i) => <TaskCardSkeleton key={i} />)
                        ) : items.length === 0 ? (
                          <EmptyColumn
                            status={col.status}
                            isFiltered={hasActiveFilters}
                            onCreateClick={canCreate ? openCreateTask : undefined}
                            onClearFilters={hasActiveFilters ? clearFilters : undefined}
                          />
                        ) : (
                          items.map((task) => (
                            <TaskCard key={task.id} task={task} onOpen={canCreate ? openEditTask : undefined} />
                          ))
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </main>
      </div>

      {/* ── Modales ─────────────────────────────────────────────────────────── */}
      {showCreate && (
        <TaskFormModal
          mode="create"
          projectName={projectName}
          members={members}
          loading={creating}
          error={createError}
          onSubmit={submitCreateTask}
          onClose={closeCreateTask}
        />
      )}

      {editingTask && (
        <TaskFormModal
          mode="edit"
          task={editingTask}
          projectName={projectName}
          members={members}
          loading={updating}
          error={editError}
          deleting={deleting}
          deleteError={deleteError}
          onSubmit={submitEditTask}
          onDelete={submitDeleteTask}
          onClose={closeEditTask}
        />
      )}
    </div>
  );
}
