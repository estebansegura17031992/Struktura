/**
 * BoardPage.jsx
 * Pantalla: Tablero Kanban de un proyecto
 * Sprint 3 · E04 · R-0401, R-0403, R-0406, AG-03, DU-03
 *
 * Desktop (md: y superior) — layout fiel al mockup aprobado (artefacto 10):
 *  - Sidebar + header, mismo patrón que ProjectsPage/ProjectMembersPage
 *  - 3 columnas siempre visibles con drag & drop (artefacto 11, R-0402,
 *    @dnd-kit/core). Cada columna es zona de drop activa aunque esté vacía
 *    (DU-03). Cambio de estado optimista con rollback si el backend rechaza
 *    el movimiento (403).
 *
 * Mobile (< md:) — layout fiel al mockup de la vista tablero móvil:
 *  - Sin sidebar. Tabs horizontales (Abierto/En proceso/Completo) en vez de
 *    3 columnas simultáneas — no hay drag & drop entre columnas porque solo
 *    una es visible a la vez.
 *  - FAB "+" fijo para "Nueva tarea" (reemplaza el botón del top bar).
 *  - TaskActionSheet (bottom sheet) reemplaza el drag: "Mover a…", "Editar
 *    tarea", "Eliminar" — este es el mecanismo real de ADR-04 para mobile,
 *    no el drag con long-press (que sigue existiendo pero es secundario:
 *    solo aplica si en algún momento se muestran 2+ columnas en pantallas
 *    intermedias).
 *
 * Solo owner/editor pueden arrastrar/cambiar estado/eliminar (mismo gate que
 * `canCreate`, igual que el backend en require_task_status_permission —
 * viewer nunca puede, ni siquiera estando asignado).
 */
import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useLocation } from "react-router-dom";
import {
  DndContext, DragOverlay, PointerSensor, TouchSensor,
  useSensor, useSensors, useDraggable, useDroppable,
} from "@dnd-kit/core";
import { useAuthStore } from "@/store/authStore";
import { logoutUser } from "@/api/auth";
import { useTasks } from "@/hooks/useTasks";
import { useMembers } from "@/hooks/useMembers";
import {
  TaskCard, TaskCardSkeleton, EmptyColumn, TaskActionSheet, TaskFormModal,
} from "@/components/tasks/TaskComponents";

// ── Drag & drop wrappers ─────────────────────────────────────────────────────

function DraggableTaskCard({ task, disabled, onOpen }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: task.id,
    disabled,
  });

  return (
    <div
      ref={setNodeRef}
      {...(disabled ? {} : { ...listeners, ...attributes })}
      style={{
        transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
        opacity: isDragging ? 0.35 : 1,
        cursor: disabled ? "default" : "grab",
      }}
    >
      <TaskCard task={task} onOpen={onOpen} />
    </div>
  );
}

function DroppableColumn({ status, children }) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  return (
    <div
      ref={setNodeRef}
      className="flex flex-col gap-3 flex-1 rounded-2xl transition-colors p-1 -m-1"
      style={isOver ? { background: "rgba(76,215,242,0.06)", outline: "2px dashed rgba(76,215,242,0.35)" } : {}}
    >
      {children}
    </div>
  );
}

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
    // Drag & drop
    dragError, moveTask,
  } = useTasks(projectId);

  // Miembros activos del proyecto — fuente del selector de asignados (solo
  // miembros activos pueden asignarse a tareas nuevas, R-0401).
  const { members } = useMembers(projectId);

  // ── Mobile: tabs + bottom sheet (ADR-04) ──────────────────────────────
  const [activeStatus, setActiveStatus] = useState("abierto");
  const [actionSheetTask, setActionSheetTask] = useState(null);

  // ── Drag & drop (desktop) ──────────────────────────────────────────────
  const [activeTask, setActiveTask] = useState(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 300, tolerance: 8 } }) // ADR-04: long-press 300ms
  );
  const allTasks = COLUMNS.flatMap((c) => columns[c.status] ?? []);

  const handleDragStart = (event) => {
    setActiveTask(allTasks.find((t) => t.id === event.active.id) ?? null);
  };

  const handleDragEnd = (event) => {
    setActiveTask(null);
    const newStatus = event.over?.id;
    const taskId = event.active?.id;
    if (!newStatus || !taskId) return;
    moveTask(taskId, newStatus);
  };

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

        {/* Sidebar — oculto en mobile (mockup usa tabs + bottom sheet en su lugar) */}
        <aside
          className="hidden md:flex w-60 shrink-0 flex-col py-4 sticky top-[57px] h-[calc(100vh-57px)] overflow-y-auto"
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
                  className="hidden md:flex items-center gap-2 px-5 py-2.5 rounded-full font-semibold text-sm transition-opacity hover:opacity-90"
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

          {/* Errores comunes a ambos layouts */}
          {(dragError || error) && (
            <div className="px-4 md:px-6 pt-4">
              {dragError && (
                <div
                  className="mb-4 px-4 py-3 rounded-xl flex items-center gap-3"
                  style={{ background: "rgba(255,180,171,0.1)", border: "1px solid rgba(255,180,171,0.3)" }}
                >
                  <span className="material-symbols-outlined text-error text-[18px]">error</span>
                  <span className="text-error text-sm">{dragError}</span>
                </div>
              )}
              {error && (
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
              )}
            </div>
          )}

          {!error && (
            <>
              {/* ── Board desktop: 3 columnas + drag & drop ─────────────────── */}
              <div className="hidden md:block flex-1 overflow-x-auto p-6">
                <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
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

                          <DroppableColumn status={col.status}>
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
                                <DraggableTaskCard
                                  key={task.id}
                                  task={task}
                                  disabled={!canCreate}
                                  onOpen={canCreate ? openEditTask : undefined}
                                />
                              ))
                            )}
                          </DroppableColumn>
                        </div>
                      );
                    })}
                  </div>

                  <DragOverlay>
                    {activeTask && (
                      <div style={{ transform: "rotate(2deg)", boxShadow: "0 12px 32px rgba(0,0,0,0.5)" }}>
                        <TaskCard task={activeTask} />
                      </div>
                    )}
                  </DragOverlay>
                </DndContext>
              </div>

              {/* ── Board mobile: tabs + una columna + bottom sheet (ADR-04) ── */}
              <div className="md:hidden flex-1 flex flex-col overflow-hidden">
                <div
                  className="flex overflow-x-auto no-scrollbar border-b flex-shrink-0"
                  style={{ borderColor: "#2D3135" }}
                >
                  {COLUMNS.map((col) => {
                    const count = columns[col.status]?.length ?? 0;
                    const active = activeStatus === col.status;
                    return (
                      <button
                        key={col.status}
                        onClick={() => setActiveStatus(col.status)}
                        className="flex-none px-5 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors"
                        style={active
                          ? { borderColor: col.dot, color: col.dot }
                          : { borderColor: "transparent", color: "#dcc1b2" }}
                      >
                        {col.label} ({loading ? "…" : count})
                      </button>
                    );
                  })}
                </div>

                <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
                  {loading ? (
                    Array.from({ length: 2 }).map((_, i) => <TaskCardSkeleton key={i} />)
                  ) : (columns[activeStatus]?.length ?? 0) === 0 ? (
                    <EmptyColumn
                      status={activeStatus}
                      isFiltered={hasActiveFilters}
                      onCreateClick={canCreate ? openCreateTask : undefined}
                      onClearFilters={hasActiveFilters ? clearFilters : undefined}
                    />
                  ) : (
                    columns[activeStatus].map((task) => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        onOpen={canCreate ? openEditTask : undefined}
                        onMore={canCreate ? setActionSheetTask : undefined}
                      />
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </main>
      </div>

      {/* FAB "Nueva tarea" — mobile, reemplaza el botón del top bar */}
      {canCreate && (
        <button
          onClick={openCreateTask}
          className="md:hidden fixed bottom-6 right-6 w-14 h-14 rounded-full shadow-lg flex items-center justify-center active:scale-90 transition-transform z-40"
          style={{ background: "#da7726", color: "#461f00" }}
          aria-label="Nueva tarea"
        >
          <span className="material-symbols-outlined text-[28px]">add</span>
        </button>
      )}

      {/* Bottom sheet de acciones — mobile (ADR-04) */}
      {actionSheetTask && (
        <TaskActionSheet
          task={actionSheetTask}
          deleting={deleting}
          deleteError={deleteError}
          onChangeStatus={moveTask}
          onEdit={openEditTask}
          onDelete={async (taskId) => {
            const ok = await submitDeleteTask(taskId);
            if (ok) setActionSheetTask(null);
          }}
          onClose={() => setActionSheetTask(null)}
        />
      )}

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
