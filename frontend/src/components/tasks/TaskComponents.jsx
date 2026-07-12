/**
 * TaskComponents.jsx
 * Componentes de la pantalla Tablero Kanban
 * Sprint 3 · E04 · R-0401, R-0403, R-0406, R-0407, DU-01, DU-03
 *
 * Exporta:
 *   TaskCard          — tarjeta Kanban (mockup #2)
 *   TaskCardSkeleton  — skeleton de carga
 *   EmptyColumn       — estado vacío por columna (con y sin filtro — AG-03/DU-03)
 *   TaskFormModal     — drawer de creación/edición de tarea (mockups #14)
 *
 * NOTA (Backend real, no el mockup visual): el DTO actual de `TaskOut`
 * (backend/app/schemas/task.py) NO incluye total_time_seconds, my_time_seconds,
 * comments_count ni is_timer_active — esos campos llegan con E05 (cronómetro,
 * Sprint 4) y E07 (comentarios, Sprint 5). Por eso esta tarjeta NO muestra
 * cronómetro ni contador de comentarios todavía, a diferencia del mockup.
 */
import React, { useState, useEffect, useRef } from "react";
import { Avatar } from "@/components/ui/DesignSystem";

// ── Prioridad ──────────────────────────────────────────────────────────────────

const PRIORITY_META = {
  high:   { label: "Alta",  dot: "#ffb4ab", color: "#ffb4ab", bg: "rgba(255,180,171,0.1)",  border: "rgba(255,180,171,0.3)" },
  medium: { label: "Media", dot: "#f6ba8b", color: "#f6ba8b", bg: "rgba(246,186,139,0.15)", border: "rgba(246,186,139,0.3)" },
  low:    { label: "Baja",  dot: "#a38c7e", color: "#dcc1b2", bg: "rgba(85,67,55,0.25)",    border: "rgba(163,140,126,0.3)" },
};

function PriorityBadge({ priority }) {
  const m = PRIORITY_META[priority] ?? PRIORITY_META.low;
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
      style={{ background: m.bg, color: m.color, border: `1px solid ${m.border}` }}
    >
      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: m.dot }} />
      {m.label}
    </span>
  );
}

// ── Badge "Vencida" (AG-02: evaluado en cliente con timezone del usuario) ──────

function isOverdue(dueDate, status) {
  if (!dueDate || status === "completo") return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(`${dueDate}T00:00:00`);
  return due < today;
}

function OverdueBadge() {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold"
      style={{ background: "rgba(255,180,171,0.15)", color: "#ffb4ab", border: "1px solid rgba(255,180,171,0.35)" }}
    >
      <span className="material-symbols-outlined text-[12px]">error</span>
      Vencida
    </span>
  );
}

// ── Fecha corta ──────────────────────────────────────────────────────────────

function formatDueDate(dueDate) {
  if (!dueDate) return null;
  const d = new Date(`${dueDate}T00:00:00`);
  return d.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}

// ── Stack de asignados — max 3 + N, grisado si is_active=false (DU-01) ────────

function AssigneeStack({ assignees = [] }) {
  if (assignees.length === 0) return null;
  const display = assignees.slice(0, 3);
  const extra = assignees.length - display.length;

  return (
    <div className="flex items-center -space-x-2">
      {display.map((a) => (
        <div
          key={a.id}
          className={`relative rounded-full ${!a.is_active ? "grayscale opacity-50" : ""}`}
          style={{ border: "2px solid #1e2023" }}
          title={a.is_active ? a.username : `${a.username} (removido del proyecto)`}
        >
          <Avatar name={a.username} src={a.avatar} size="sm" />
        </div>
      ))}
      {extra > 0 && (
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold text-on-surface-variant"
          style={{ background: "#333538", border: "2px solid #1e2023" }}
        >
          +{extra}
        </div>
      )}
    </div>
  );
}

// ── TaskCard ───────────────────────────────────────────────────────────────────

export function TaskCard({ task, onOpen }) {
  const overdue = isOverdue(task.due_date, task.status);
  const hasRemoved = task.assignees?.some((a) => !a.is_active);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onOpen?.(task)}
      onKeyDown={(e) => { if (e.key === "Enter") onOpen?.(task); }}
      className="rounded-xl p-4 flex flex-col gap-3 cursor-pointer transition-all"
      style={{ background: "#1e2023", border: "1px solid #2D3135" }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#4cd7f2")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#2D3135")}
    >
      {/* Header */}
      <div className="flex justify-between items-start">
        <span className="font-mono text-[10px] text-on-surface-variant opacity-60">
          #TASK-{task.task_number}
        </span>
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-2 items-center">
        <PriorityBadge priority={task.priority} />
        {overdue && <OverdueBadge />}
      </div>

      {/* Título */}
      <h3 className="text-on-surface text-sm font-medium leading-tight line-clamp-2">
        {task.title}
      </h3>

      {/* Footer: fecha + asignados */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-1.5 text-on-surface-variant text-[12px]">
          {task.due_date && (
            <>
              <span className="material-symbols-outlined text-[15px]">calendar_today</span>
              <span>{formatDueDate(task.due_date)}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          {hasRemoved && (
            <span
              className="text-[9px] font-medium px-1.5 py-0.5 rounded-full text-on-surface-variant"
              style={{ background: "#333538", border: "1px solid #2D3135" }}
            >
              Removido
            </span>
          )}
          <AssigneeStack assignees={task.assignees} />
        </div>
      </div>
    </div>
  );
}

// ── Skeleton ───────────────────────────────────────────────────────────────────

export function TaskCardSkeleton() {
  return (
    <div
      className="rounded-xl p-4 flex flex-col gap-3 animate-pulse"
      style={{ background: "#1e2023", border: "1px solid #2D3135" }}
    >
      <div className="h-3 w-16 rounded-full bg-surface-variant/40" />
      <div className="h-5 w-20 rounded-full bg-surface-variant/50" />
      <div className="h-4 w-full rounded-full bg-surface-variant/50" />
      <div className="h-4 w-2/3 rounded-full bg-surface-variant/40" />
      <div className="flex justify-between pt-1">
        <div className="h-3 w-14 rounded-full bg-surface-variant/40" />
        <div className="h-7 w-7 rounded-full bg-surface-variant/50" />
      </div>
    </div>
  );
}

// ── EmptyColumn — AG-03 (CTA solo en Abierto sin filtro) / DU-03 (con filtro) ──

export function EmptyColumn({ status, isFiltered, onCreateClick, onClearFilters }) {
  if (isFiltered) {
    return (
      <div
        className="flex-1 rounded-2xl flex flex-col items-center justify-center p-8 gap-3 min-h-[220px]"
        style={{ background: "rgba(76,215,242,0.04)", border: "2px dashed rgba(76,215,242,0.25)" }}
      >
        <span className="material-symbols-outlined text-secondary text-[32px] opacity-60">search_off</span>
        <p className="text-on-surface text-sm font-medium text-center">Sin tareas con este filtro</p>
        <p className="text-on-surface-variant text-xs text-center max-w-[180px]">
          No se encontraron tareas que coincidan con los filtros aplicados.
        </p>
        {onClearFilters && (
          <button onClick={onClearFilters} className="text-primary text-xs font-medium hover:underline">
            Limpiar filtros para ver más
          </button>
        )}
      </div>
    );
  }

  if (status === "abierto") {
    return (
      <div
        className="flex-1 rounded-2xl flex flex-col items-center justify-center p-8 gap-3 min-h-[220px]"
        style={{ background: "transparent", border: "2px dashed #2D3135" }}
      >
        <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ background: "rgba(76,215,242,0.1)" }}>
          <span className="material-symbols-outlined text-secondary text-[24px]">add</span>
        </div>
        <p className="text-on-surface text-sm font-medium text-center">No hay tareas todavía</p>
        {onCreateClick && (
          <button
            onClick={onCreateClick}
            className="flex items-center gap-2 px-4 py-2 rounded-full font-semibold text-xs transition-opacity hover:opacity-90"
            style={{ background: "#da7726", color: "#461f00" }}
          >
            <span className="material-symbols-outlined text-[16px]">add</span>
            Crear primera tarea
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className="flex-1 rounded-2xl flex flex-col items-center justify-center p-8 gap-2 min-h-[220px]"
      style={{ background: "transparent", border: "2px dashed #2D3135" }}
    >
      <span className="material-symbols-outlined text-on-surface-variant text-[28px] opacity-30">inbox</span>
      <p className="text-on-surface-variant text-xs text-center">Sin tareas en esta columna</p>
    </div>
  );
}

// ── TaskFormModal — Crear y Editar (mockup #14) ───────────────────────────────
// El status se edita aquí visualmente pero se envía por su propio endpoint
// (PATCH /tasks/{id}/status) — el hook (useTasks) decide qué endpoints llamar.
// Igual para assignee_ids: viaja por PATCH /tasks/{id}/assignees para no
// saltarse la lógica ADR-03 (detener timer al pasar a 2+ asignados) que solo
// vive en ese endpoint dedicado.

const STATUS_OPTIONS = [
  { value: "abierto",    label: "Abierto",    dot: "#ffb786" },
  { value: "en_proceso", label: "En proceso", dot: "#4cd7f2" },
  { value: "completo",   label: "Completo",   dot: "#4ade80" },
];

export function TaskFormModal({
  mode = "create",
  task = null,
  projectName,
  members = [],
  loading,
  error,
  deleting,
  deleteError,
  onSubmit,
  onDelete,
  onClose,
}) {
  const isCreate = mode === "create";

  const [title, setTitle] = useState(task?.title ?? "");
  const [description, setDescription] = useState(task?.description ?? "");
  const [priority, setPriorityVal] = useState(task?.priority ?? "high");
  const [status, setStatus] = useState(task?.status ?? "abierto");
  const [dueDate, setDueDate] = useState(task?.due_date ?? "");
  const [assigneeIds, setAssigneeIds] = useState((task?.assignees ?? []).map((a) => a.id));
  const [titleError, setTitleError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [open, setOpen] = useState(false);
  const titleRef = useRef(null);

  useEffect(() => {
    const t = requestAnimationFrame(() => setOpen(true));
    return () => cancelAnimationFrame(t);
  }, []);

  useEffect(() => {
    setTimeout(() => titleRef.current?.focus(), 320);
  }, []);

  useEffect(() => {
    const h = (e) => { if (e.key === "Escape") handleClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleClose = () => {
    setOpen(false);
    setTimeout(onClose, 300);
  };

  const validateTitle = (val) => {
    if (!val.trim()) { setTitleError("El nombre es obligatorio"); return false; }
    setTitleError("");
    return true;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validateTitle(title)) return;
    onSubmit({
      title: title.trim(),
      description: description.trim() || null,
      priority,
      due_date: dueDate || null,
      assignee_ids: assigneeIds,
      ...(isCreate ? {} : { status }),
    });
  };

  const toggleAssignee = (userId) => {
    setAssigneeIds((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId]
    );
  };

  // Los ya asignados-pero-removidos (DU-01) no están en `members` (solo activos);
  // se muestran igual como chip grisado, no removible salvo des-seleccionar.
  const removedAssignees = (task?.assignees ?? []).filter(
    (a) => !a.is_active && assigneeIds.includes(a.id)
  );
  const timerWarning = assigneeIds.length > 1;

  return (
    <>
      <div
        className="fixed inset-0 z-40 transition-opacity duration-300"
        style={{ background: "rgba(17,19,22,0.75)", backdropFilter: "blur(4px)", opacity: open ? 1 : 0 }}
        onClick={handleClose}
      />

      <div
        role="dialog" aria-modal="true" aria-labelledby="task-drawer-title"
        className="fixed top-0 right-0 h-screen z-50 flex flex-col shadow-2xl transition-transform duration-300 ease-out"
        style={{
          width: "min(520px, 100vw)",
          background: "#111316",
          borderLeft: "1px solid #2D3135",
          transform: open ? "translateX(0)" : "translateX(100%)",
        }}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 flex-shrink-0 border-b" style={{ borderColor: "#2D3135" }}>
          <div>
            <div className="flex items-center gap-2 text-on-surface-variant text-xs mb-1">
              <span className="material-symbols-outlined text-[16px]">folder</span>
              Proyecto: {projectName ?? "—"}
            </div>
            <div className="flex items-baseline gap-3">
              <h2 id="task-drawer-title" className="font-['Poppins'] font-semibold text-on-surface text-xl">
                {isCreate ? "Nueva tarea" : "Editar tarea"}
              </h2>
              {!isCreate && (
                <span className="font-mono text-sm text-on-surface-variant opacity-60">#TASK-{task.task_number}</span>
              )}
            </div>
          </div>
          <button
            onClick={handleClose}
            className="w-9 h-9 rounded-full flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-colors"
            onMouseEnter={(e) => (e.currentTarget.style.background = "#1e2023")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            aria-label="Cerrar"
          >
            <span className="material-symbols-outlined text-[22px]">close</span>
          </button>
        </div>

        {/* Contenido */}
        <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
          <div className="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-6">

            {/* Nombre */}
            <div>
              <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest block mb-2">
                Nombre de la tarea <span className="text-error">*</span>
              </label>
              <input
                ref={titleRef}
                type="text"
                value={title}
                onChange={(e) => { setTitle(e.target.value); if (titleError) validateTitle(e.target.value); }}
                onBlur={() => validateTitle(title)}
                maxLength={200}
                placeholder="Nombre de la tarea"
                className="w-full rounded-xl px-4 py-3 text-base font-medium text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none transition-all"
                style={{ background: "#1e2023", border: titleError ? "1px solid #ffb4ab" : "1px solid #554337" }}
                required
              />
              {titleError && (
                <div className="flex items-center gap-1.5 mt-2">
                  <span className="material-symbols-outlined text-error text-[14px]">error</span>
                  <span className="text-error text-xs">{titleError}</span>
                </div>
              )}
            </div>

            {/* Descripción */}
            <div>
              <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest block mb-2">
                Descripción
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                maxLength={2000}
                rows={4}
                placeholder="Descripción opcional…"
                className="w-full rounded-xl px-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none transition-all resize-y"
                style={{ background: "#1e2023", border: "1px solid #554337" }}
              />
            </div>

            {/* Prioridad + Estado */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest block mb-2">Prioridad</label>
                <div className="flex p-1 rounded-full" style={{ background: "#1e2023", border: "1px solid #554337" }}>
                  {["high", "medium", "low"].map((val) => {
                    const m = PRIORITY_META[val];
                    const active = priority === val;
                    return (
                      <button
                        type="button"
                        key={val}
                        onClick={() => setPriorityVal(val)}
                        className="flex-1 py-1.5 text-[11px] font-bold uppercase tracking-wider rounded-full transition-colors"
                        style={active
                          ? { background: m.dot, color: "#1a1c1f" }
                          : { color: "#dcc1b2" }}
                      >
                        {m.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest block mb-2">
                  {isCreate ? "Estado inicial" : "Estado"}
                </label>
                {isCreate ? (
                  <div
                    className="w-full rounded-xl px-4 py-2.5 flex items-center gap-2 text-on-surface-variant text-sm"
                    style={{ background: "rgba(51,53,56,0.4)", border: "1px solid rgba(85,67,55,0.3)", cursor: "not-allowed" }}
                  >
                    <span className="w-2 h-2 rounded-full" style={{ background: "#ffb786" }} />
                    Abierto
                  </div>
                ) : (
                  <>
                    <div className="relative">
                      <select
                        value={status}
                        onChange={(e) => setStatus(e.target.value)}
                        className="w-full appearance-none rounded-xl px-4 py-2.5 pl-9 text-sm font-medium text-on-surface focus:outline-none cursor-pointer"
                        style={{ background: "#1e2023", border: "1px solid #554337" }}
                      >
                        {STATUS_OPTIONS.map((s) => (
                          <option key={s.value} value={s.value} style={{ background: "#1e2023" }}>{s.label}</option>
                        ))}
                      </select>
                      <span
                        className="absolute left-4 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full pointer-events-none"
                        style={{ background: STATUS_OPTIONS.find((s) => s.value === status)?.dot }}
                      />
                      <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[16px] pointer-events-none">expand_more</span>
                    </div>
                    {status !== task?.status && (
                      <div className="flex items-center gap-1.5 mt-2">
                        <span className="material-symbols-outlined text-[14px] text-on-surface-variant">info</span>
                        <p className="text-[11px] text-on-surface-variant">Se detendrá el cronómetro activo si existe</p>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>

            {/* Fecha límite */}
            <div>
              <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest block mb-2">Fecha límite</label>
              <div className="relative">
                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">calendar_today</span>
                <input
                  type="date"
                  value={dueDate ?? ""}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="w-full rounded-xl pl-11 pr-4 py-3 text-sm text-on-surface focus:outline-none transition-all"
                  style={{ background: "#1e2023", border: "1px solid #554337" }}
                />
              </div>
            </div>

            {/* Asignados */}
            <div>
              <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest block mb-2">Asignados</label>
              <div
                className="flex flex-wrap gap-2 p-2 rounded-xl min-h-[52px]"
                style={{ background: "#1e2023", border: "1px solid #554337" }}
              >
                {members.filter((m) => assigneeIds.includes(m.user_id)).map((m) => (
                  <span
                    key={m.user_id}
                    className="flex items-center gap-2 rounded-full pl-1 pr-2 py-1 text-sm text-on-surface"
                    style={{ background: "#282a2d", border: "1px solid #554337" }}
                  >
                    <Avatar name={m.user?.username} size="sm" />
                    {m.user?.username}
                    <button type="button" onClick={() => toggleAssignee(m.user_id)} className="material-symbols-outlined text-[16px] hover:text-error">close</button>
                  </span>
                ))}

                {removedAssignees.map((a) => (
                  <span
                    key={a.id}
                    className="flex items-center gap-2 rounded-full pl-1 pr-2 py-1 text-sm text-on-surface-variant grayscale opacity-70"
                    style={{ background: "#282a2d", border: "1px solid rgba(85,67,55,0.3)" }}
                  >
                    <Avatar name={a.username} size="sm" />
                    {a.username}
                    <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded" style={{ background: "#333538" }}>Removido</span>
                    <button type="button" onClick={() => toggleAssignee(a.id)} className="material-symbols-outlined text-[16px] hover:text-error">close</button>
                  </span>
                ))}

                {members.filter((m) => m.is_active && !assigneeIds.includes(m.user_id)).map((m) => (
                  <button
                    type="button"
                    key={m.user_id}
                    onClick={() => toggleAssignee(m.user_id)}
                    title={`Asignar a ${m.user?.username}`}
                    className="flex items-center gap-1 rounded-full px-2 py-1 text-xs text-on-surface-variant hover:text-secondary transition-colors"
                    style={{ border: "1px dashed #a38c7e" }}
                  >
                    <span className="material-symbols-outlined text-[14px]">add</span>
                    {m.user?.username}
                  </button>
                ))}
              </div>

              {timerWarning && (
                <div className="flex gap-3 p-3 mt-3 rounded-xl" style={{ background: "rgba(246,186,139,0.1)", border: "1px solid rgba(246,186,139,0.25)" }}>
                  <span className="material-symbols-outlined text-tertiary text-[18px]">info</span>
                  <p className="text-xs text-on-surface-variant leading-relaxed">
                    El cronómetro estará deshabilitado para tareas con múltiples asignados.
                  </p>
                </div>
              )}
            </div>

            {/* Error API */}
            {error && (
              <div className="flex items-start gap-3 rounded-xl px-4 py-3" style={{ background: "rgba(255,180,171,0.1)", border: "1px solid rgba(255,180,171,0.3)" }}>
                <span className="material-symbols-outlined text-error text-[18px] flex-shrink-0 mt-0.5">error</span>
                <p className="text-error text-sm leading-relaxed">{error}</p>
              </div>
            )}

            {/* Zona de peligro — solo en edición */}
            {!isCreate && onDelete && (
              <div className="rounded-xl p-4 flex flex-col gap-3" style={{ background: "rgba(255,180,171,0.06)", border: "1px solid rgba(255,180,171,0.2)" }}>
                {!confirmDelete ? (
                  <button
                    type="button"
                    onClick={() => setConfirmDelete(true)}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-full text-sm font-semibold transition-all hover:opacity-90"
                    style={{ color: "#ffb4ab", border: "1px solid rgba(255,180,171,0.3)" }}
                  >
                    <span className="material-symbols-outlined text-[18px]">delete</span>
                    Eliminar tarea
                  </button>
                ) : (
                  <>
                    <p className="text-on-surface text-sm">¿Eliminar esta tarea permanentemente? No se puede deshacer (AG-04).</p>
                    {deleteError && <p className="text-error text-xs">{deleteError}</p>}
                    <div className="flex gap-3">
                      <button
                        type="button"
                        onClick={() => setConfirmDelete(false)}
                        className="flex-1 py-2 rounded-full text-sm text-on-surface-variant"
                        style={{ border: "1px solid #2D3135" }}
                      >
                        Cancelar
                      </button>
                      <button
                        type="button"
                        onClick={onDelete}
                        disabled={deleting}
                        className="flex-1 py-2 rounded-full text-sm font-semibold disabled:opacity-50"
                        style={{ background: "rgba(147,0,10,0.4)", color: "#ffb4ab", border: "1px solid rgba(255,180,171,0.3)" }}
                      >
                        {deleting ? "Eliminando…" : "Confirmar"}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Footer fijo */}
          <div className="flex items-center gap-3 px-6 py-4 flex-shrink-0 border-t" style={{ borderColor: "#2D3135" }}>
            <button
              type="button"
              onClick={handleClose}
              disabled={loading}
              className="flex-1 py-3 rounded-full text-sm font-semibold transition-all disabled:opacity-50 hover:opacity-80"
              style={{ background: "#1e2023", color: "#e2e2e6", border: "1px solid #2D3135" }}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !title.trim()}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-full text-sm font-bold transition-all disabled:opacity-50 hover:opacity-90 active:scale-95"
              style={{ background: "#da7726", color: "#fff" }}
            >
              {loading && (
                <span className="w-4 h-4 rounded-full border-2 flex-shrink-0" style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "#fff", animation: "spin 1s linear infinite" }} />
              )}
              {loading ? (isCreate ? "Creando…" : "Guardando…") : (isCreate ? "Crear tarea" : "Guardar cambios")}
            </button>
          </div>
        </form>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  );
}
