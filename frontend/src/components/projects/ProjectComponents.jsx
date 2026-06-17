/**
 * ProjectComponents.jsx
 * Componentes de la pantalla Proyectos
 * Sprint 2 · E03 · R-0301 a R-0303
 *
 * Exporta:
 *   ProjectCard         — tarjeta en vista grid
 *   ProjectRow          — fila en vista lista
 *   ProjectCardSkeleton — skeleton grid
 *   ProjectRowSkeleton  — skeleton list
 *   ProjectEmptyState   — estado vacío
 *   ProjectFormModal    — modal crear / editar
 *   DeleteConfirmModal  — modal confirmación eliminación
 *   RoleChip            — chip de rol (owner/editor/viewer)
 *   MemberAvatarStack   — stack de avatares de miembros
 */
import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

// ── Constantes de rol ──────────────────────────────────────────────────────────

const ROLE_META = {
  owner:  { label: "Owner",  color: "#ffb786", bg: "rgba(255,183,134,0.15)", border: "rgba(255,183,134,0.3)"  },
  editor: { label: "Editor", color: "#a78bfa", bg: "rgba(167,139,250,0.15)", border: "rgba(167,139,250,0.3)"  },
  viewer: { label: "Viewer", color: "#94a3b8", bg: "rgba(148,163,184,0.12)", border: "rgba(148,163,184,0.25)" },
};

// ── RoleChip ───────────────────────────────────────────────────────────────────

export function RoleChip({ role, size = "sm" }) {
  const m = ROLE_META[role?.toLowerCase()] ?? ROLE_META.viewer;
  const px = size === "sm" ? "px-2.5 py-0.5 text-[10px]" : "px-3 py-1 text-xs";
  return (
    <span
      className={`inline-flex items-center font-bold rounded-full ${px}`}
      style={{ color: m.color, background: m.bg, border: `1px solid ${m.border}` }}
    >
      {m.label}
    </span>
  );
}

// ── MemberAvatarStack ──────────────────────────────────────────────────────────

export function MemberAvatarStack({ count = 0 }) {
  const display = Math.min(count, 3);
  const extra   = count > 3 ? count - 3 : 0;
  const colors  = ["#da7726", "#4cd7f2", "#a78bfa", "#f6ba8b"];
  return (
    <div className="flex items-center">
      {Array.from({ length: display }).map((_, i) => (
        <div
          key={i}
          className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold"
          style={{
            background: colors[i % colors.length],
            color: "#111316",
            border: "2px solid #1a1c1f",
            marginLeft: i > 0 ? -8 : 0,
            zIndex: display - i,
          }}
        >
          {String.fromCharCode(65 + i)}
        </div>
      ))}
      {extra > 0 && (
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold"
          style={{
            background: "#333538",
            color: "#dcc1b2",
            border: "2px solid #1a1c1f",
            marginLeft: -8,
          }}
        >
          +{extra}
        </div>
      )}
    </div>
  );
}

// ── ProjectIcon ────────────────────────────────────────────────────────────────

function ProjectIcon({ name }) {
  const colors = [
    { bg: "rgba(218,119,38,0.2)", color: "#ffb786" },
    { bg: "rgba(76,215,242,0.2)", color: "#4cd7f2" },
    { bg: "rgba(167,139,250,0.2)", color: "#a78bfa" },
    { bg: "rgba(246,186,139,0.2)", color: "#f6ba8b" },
  ];
  const idx = (name?.charCodeAt(0) ?? 0) % colors.length;
  const { bg, color } = colors[idx];
  return (
    <div
      className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
      style={{ background: bg }}
    >
      <span className="material-symbols-outlined text-[20px]" style={{ color }}>
        folder_managed
      </span>
    </div>
  );
}

// ── ActionsMenu ────────────────────────────────────────────────────────────────

function ActionsMenu({ project, myRole, onEdit, onDelete, onMembers, onView }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const canEdit   = ["owner", "editor", "admin"].includes(myRole);
  const canDelete = myRole === "owner" || myRole === "admin";

  useEffect(() => {
    const h = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    if (open) document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(v => !v); }}
        className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-variant/60 hover:text-on-surface transition-colors"
        aria-label="Acciones"
      >
        <span className="material-symbols-outlined text-[20px]">more_vert</span>
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-1 w-44 rounded-xl py-1 z-30 shadow-xl"
          style={{ background: "#1e2023", border: "1px solid #2D3135" }}
        >
          {/* Ver proyecto */}
          <button
            onClick={(e) => { e.stopPropagation(); setOpen(false); onView(project); }}
            className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40 transition-colors"
          >
            <span className="material-symbols-outlined text-[16px]">open_in_new</span>
            Ver proyecto
          </button>

          {/* Editar */}
          {canEdit && (
            <button
              onClick={(e) => { e.stopPropagation(); setOpen(false); onEdit(project); }}
              className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40 transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">edit</span>
              Editar
            </button>
          )}

          {/* Miembros */}
          <button
            onClick={(e) => { e.stopPropagation(); setOpen(false); onMembers(project); }}
            className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/40 transition-colors"
          >
            <span className="material-symbols-outlined text-[16px]">group</span>
            Miembros
          </button>

          {/* Eliminar */}
          {canDelete && (
            <>
              <div className="my-1 border-t" style={{ borderColor: "#2D3135" }} />
              <button
                onClick={(e) => { e.stopPropagation(); setOpen(false); onDelete(project); }}
                className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-error hover:bg-error/10 transition-colors"
              >
                <span className="material-symbols-outlined text-[16px]">delete</span>
                Eliminar
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── ProjectCard (vista grid) ───────────────────────────────────────────────────

export function ProjectCard({ project, onEdit, onDelete, onMembers, onView }) {
  const myRole = project.my_role ?? "viewer";
  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-4 cursor-pointer transition-all duration-200 hover:-translate-y-1"
      style={{
        background: "#1a1c1f",
        border: "1px solid #2D3135",
        boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = "#4cd7f2"}
      onMouseLeave={e => e.currentTarget.style.borderColor = "#2D3135"}
      onClick={() => onView(project)}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <ProjectIcon name={project.name} />
          <RoleChip role={myRole} />
        </div>
        <ActionsMenu
          project={project}
          myRole={myRole}
          onEdit={onEdit}
          onDelete={onDelete}
          onMembers={onMembers}
          onView={onView}
        />
      </div>

      {/* Nombre y descripción */}
      <div className="flex-1">
        <h3 className="font-['Poppins'] font-semibold text-on-surface text-base mb-1 line-clamp-1">
          {project.name}
        </h3>
        <p className="text-on-surface-variant text-sm line-clamp-2 leading-relaxed">
          {project.description || <span className="italic opacity-50">Sin descripción</span>}
        </p>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-1 border-t" style={{ borderColor: "#2D3135" }}>
        <MemberAvatarStack count={project.member_count ?? 0} />
        <span className="text-on-surface-variant text-xs">
          {formatRelative(project.created_at)}
        </span>
      </div>
    </div>
  );
}

// ── Tarjeta "Crear proyecto" (ghost card en grid) ─────────────────────────────

export function CreateProjectCard({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="rounded-2xl p-5 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all duration-200 hover:-translate-y-1 w-full min-h-[200px]"
      style={{
        background: "transparent",
        border: "2px dashed #2D3135",
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = "#4cd7f2"}
      onMouseLeave={e => e.currentTarget.style.borderColor = "#2D3135"}
    >
      <div
        className="w-12 h-12 rounded-full flex items-center justify-center"
        style={{ background: "rgba(76,215,242,0.1)" }}
      >
        <span className="material-symbols-outlined text-secondary text-[24px]">add</span>
      </div>
      <div className="text-center">
        <p className="font-['Poppins'] font-semibold text-on-surface text-sm mb-1">Crear Proyecto</p>
        <p className="text-on-surface-variant text-xs">Inicia un nuevo flujo de trabajo estructurado para tu equipo.</p>
      </div>
    </button>
  );
}

// ── ProjectRow (vista lista) ───────────────────────────────────────────────────

export function ProjectRow({ project, onEdit, onDelete, onMembers, onView }) {
  const myRole = project.my_role ?? "viewer";
  return (
    <tr
      className="group border-b transition-colors cursor-pointer hover:bg-surface-container"
      style={{ borderColor: "#2D3135" }}
      onClick={() => onView(project)}
    >
      {/* Proyecto */}
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <ProjectIcon name={project.name} />
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="font-semibold text-on-surface text-sm">{project.name}</span>
              <RoleChip role={myRole} />
            </div>
          </div>
        </div>
      </td>
      {/* Descripción */}
      <td className="px-6 py-4 text-on-surface-variant text-sm max-w-xs">
        <span className="line-clamp-1">{project.description || "—"}</span>
      </td>
      {/* Equipo */}
      <td className="px-6 py-4">
        <div className="flex items-center gap-2">
          <MemberAvatarStack count={project.member_count ?? 0} />
          <span className="text-on-surface-variant text-xs">{project.member_count ?? 0}</span>
        </div>
      </td>
      {/* Creado */}
      <td className="px-6 py-4 text-on-surface-variant text-sm whitespace-nowrap">
        {formatRelative(project.created_at)}
      </td>
      {/* Acciones — stopPropagation para no disparar onView de la fila */}
      <td className="px-6 py-4 text-right" onClick={e => e.stopPropagation()}>
        <ActionsMenu
          project={project}
          myRole={myRole}
          onEdit={onEdit}
          onDelete={onDelete}
          onMembers={onMembers}
          onView={onView}
        />
      </td>
    </tr>
  );
}

// ── Skeletons ──────────────────────────────────────────────────────────────────

export function ProjectCardSkeleton() {
  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-4 animate-pulse"
      style={{ background: "#1a1c1f", border: "1px solid #2D3135" }}
    >
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-surface-variant/50" />
        <div className="w-16 h-5 rounded-full bg-surface-variant/50" />
      </div>
      <div className="flex flex-col gap-2">
        <div className="h-4 bg-surface-variant/50 rounded-full w-3/4" />
        <div className="h-3 bg-surface-variant/40 rounded-full w-full" />
        <div className="h-3 bg-surface-variant/30 rounded-full w-2/3" />
      </div>
      <div className="flex items-center justify-between pt-1 border-t" style={{ borderColor: "#2D3135" }}>
        <div className="flex -space-x-2">
          {[1, 2].map(i => (
            <div key={i} className="w-7 h-7 rounded-full bg-surface-variant/50" style={{ marginLeft: i > 1 ? -8 : 0 }} />
          ))}
        </div>
        <div className="h-3 w-16 rounded-full bg-surface-variant/40" />
      </div>
    </div>
  );
}

export function ProjectRowSkeleton() {
  return (
    <tr className="border-b animate-pulse" style={{ borderColor: "#2D3135" }}>
      {[200, 280, 80, 100, 40].map((w, i) => (
        <td key={i} className="px-6 py-4">
          <div className="h-4 bg-surface-variant/40 rounded-full" style={{ width: w }} />
        </td>
      ))}
    </tr>
  );
}

// ── Empty state ────────────────────────────────────────────────────────────────

export function ProjectEmptyState({ onCreateClick }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center"
        style={{ background: "rgba(76,215,242,0.1)" }}
      >
        <span className="material-symbols-outlined text-secondary text-[32px]">folder_open</span>
      </div>
      <div className="text-center">
        <p className="font-['Poppins'] font-semibold text-on-surface text-base mb-1">No tienes proyectos aún</p>
        <p className="text-on-surface-variant text-sm">Crea tu primer proyecto para empezar a organizar tu trabajo.</p>
      </div>
      <button
        onClick={onCreateClick}
        className="flex items-center gap-2 px-6 py-2.5 rounded-full font-semibold text-sm transition-opacity hover:opacity-90"
        style={{ background: "#da7726", color: "#461f00" }}
      >
        <span className="material-symbols-outlined text-[18px]">add</span>
        Crear primer proyecto
      </button>
    </div>
  );
}

// ── ProjectFormModal — Crear y Editar ─────────────────────────────────────────

const STATUS_OPTIONS = [
  { value: "active",    label: "En progreso", dot: "#4cd7f2" },
  { value: "paused",    label: "En pausa",    dot: "#f6ba8b" },
  { value: "completed", label: "Completado",  dot: "#4ade80" },
  { value: "archived",  label: "Archivado",   dot: "#94a3b8" },
];

const PRIORITY_OPTIONS = [
  { value: "high",   label: "Alta",  icon: "!", color: "#f6ba8b" },
  { value: "medium", label: "Media", icon: "~", color: "#4cd7f2" },
  { value: "low",    label: "Baja",  icon: "↓", color: "#94a3b8" },
];

export function ProjectFormModal({ mode = "create", project = null, loading, error, onSubmit, onClose, onDelete }) {
  const [name, setName]               = useState(project?.name ?? "");
  const [description, setDescription] = useState(project?.description ?? "");
  const [status, setStatus]           = useState(project?.status ?? "active");
  const [priority, setPriority]       = useState(project?.priority ?? "high");
  const [nameError, setNameError]     = useState("");
  const [open, setOpen]               = useState(false);
  const nameRef = useRef(null);

  const isCreate = mode === "create";

  useEffect(() => {
    const t = requestAnimationFrame(() => setOpen(true));
    return () => cancelAnimationFrame(t);
  }, []);

  useEffect(() => {
    setTimeout(() => nameRef.current?.focus(), 320);
  }, []);

  useEffect(() => {
    const h = (e) => { if (e.key === "Escape") handleClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  const handleClose = () => {
    setOpen(false);
    setTimeout(onClose, 300);
  };

  const validateName = (val) => {
    if (!val.trim()) { setNameError("El nombre es obligatorio"); return false; }
    setNameError("");
    return true;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validateName(name)) return;
    onSubmit({
      name: name.trim(),
      description: description.trim() || null,
      ...(isCreate ? {} : { status, priority }),
    });
  };

  const currentStatus   = STATUS_OPTIONS.find(s => s.value === status)    ?? STATUS_OPTIONS[0];
  const currentPriority = PRIORITY_OPTIONS.find(p => p.value === priority) ?? PRIORITY_OPTIONS[0];

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 transition-opacity duration-300"
        style={{ background: "rgba(17,19,22,0.75)", backdropFilter: "blur(4px)", opacity: open ? 1 : 0 }}
        onClick={handleClose}
      />

      {/* Drawer */}
      <div
        role="dialog" aria-modal="true" aria-labelledby="drawer-title"
        className="fixed top-0 right-0 h-screen z-50 flex flex-col shadow-2xl transition-transform duration-300 ease-out"
        style={{
          width: "min(520px, 100vw)",
          background: "#111316",
          borderLeft: "1px solid #2D3135",
          transform: open ? "translateX(0)" : "translateX(100%)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4 flex-shrink-0 border-b"
          style={{ borderColor: "#2D3135" }}
        >
          <div className="flex items-center gap-3">
            {!isCreate && (
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "rgba(255,183,134,0.15)" }}>
                <span className="material-symbols-outlined text-primary text-[18px]">edit_note</span>
              </div>
            )}
            <h2 id="drawer-title" className="font-['Poppins'] font-semibold text-on-surface text-xl">
              {isCreate ? "Nuevo proyecto" : "Editar proyecto"}
            </h2>
          </div>
          <button
            onClick={handleClose}
            className="w-9 h-9 rounded-full flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-colors"
            onMouseEnter={e => e.currentTarget.style.background = "#1e2023"}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}
            aria-label="Cerrar"
          >
            <span className="material-symbols-outlined text-[22px]">close</span>
          </button>
        </div>

        {/* Contenido scrollable */}
        <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
          <div className="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-5">

            {/* Imagen preview — solo en edición */}
            {!isCreate && (
              <div className="rounded-xl overflow-hidden flex-shrink-0" style={{ border: "1px solid #2D3135" }}>
                <div
                  className="h-44 flex items-center justify-center relative"
                  style={{ background: "linear-gradient(135deg, #0c0e11 0%, #1a1c1f 50%, #0c0e11 100%)" }}
                >
                  <div className="flex items-end gap-1 opacity-40">
                    {[30,50,35,70,45,80,55,90,60,75,40,65,85,50,70].map((h, i) => (
                      <div key={i} className="w-3 rounded-sm" style={{ height: h, background: i === 9 ? "#4cd7f2" : "#da7726", opacity: 0.7 + (i % 3) * 0.1 }} />
                    ))}
                  </div>
                  <div className="absolute top-3 right-3 flex gap-2">
                    <div className="px-2 py-0.5 rounded text-[10px] font-medium" style={{ background: "#1e2023", color: "#4cd7f2", border: "1px solid #2D3135" }}>
                      {project?.name?.slice(0, 16) ?? "Proyecto"}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Nombre */}
            <div>
              <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest block mb-2">
                Nombre del proyecto <span className="text-error">*</span>
              </label>
              <div className="relative">
                <input
                  ref={nameRef}
                  type="text"
                  value={name}
                  onChange={e => { setName(e.target.value); if (nameError) validateName(e.target.value); }}
                  onBlur={() => validateName(name)}
                  maxLength={100}
                  placeholder="Ej: Portal de Clientes"
                  className="w-full rounded-xl px-4 py-3 pr-16 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none transition-all"
                  style={{
                    background: "#1e2023",
                    border: nameError ? "1px solid #ffb4ab" : name.trim() ? "1px solid #4cd7f2" : "1px solid #554337",
                  }}
                  required
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[11px] pointer-events-none">
                  {name.length}/100
                </span>
              </div>
              {nameError && (
                <div className="flex items-center gap-1.5 mt-2">
                  <span className="material-symbols-outlined text-error text-[14px]" style={{ fontVariationSettings: "'FILL' 1" }}>error</span>
                  <span className="text-error text-xs">{nameError}</span>
                </div>
              )}
            </div>

            {/* Descripción */}
            <div>
              <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest block mb-2">
                Descripción
              </label>
              <div className="relative">
                <textarea
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  maxLength={500}
                  rows={4}
                  placeholder="Describe brevemente los objetivos de este proyecto..."
                  className="w-full rounded-xl px-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none transition-all resize-none pb-6"
                  style={{
                    background: "#1e2023",
                    border: description ? "1px solid #4cd7f2" : "1px solid #554337",
                  }}
                />
                <span className="absolute right-4 bottom-3 text-on-surface-variant text-[11px] pointer-events-none">
                  {description.length}/500
                </span>
              </div>
            </div>

            {/* Estado y Prioridad — solo en edición */}
            {!isCreate && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest block mb-2">
                    Estado
                  </label>
                  <div className="relative">
                    <select
                      value={status}
                      onChange={e => setStatus(e.target.value)}
                      className="w-full appearance-none rounded-xl px-4 py-3 pl-9 text-sm font-medium focus:outline-none transition-all cursor-pointer"
                      style={{ background: "#1e2023", border: "1px solid #554337", color: currentStatus.dot }}
                    >
                      {STATUS_OPTIONS.map(s => (
                        <option key={s.value} value={s.value} style={{ color: s.dot, background: "#1e2023" }}>{s.label}</option>
                      ))}
                    </select>
                    <div
                      className="absolute left-4 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full pointer-events-none"
                      style={{ background: currentStatus.dot }}
                    />
                    <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[16px] pointer-events-none">
                      expand_more
                    </span>
                  </div>
                </div>
                <div>
                  <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest block mb-2">
                    Prioridad
                  </label>
                  <div className="relative">
                    <select
                      value={priority}
                      onChange={e => setPriority(e.target.value)}
                      className="w-full appearance-none rounded-xl px-4 py-3 pl-9 text-sm font-medium focus:outline-none transition-all cursor-pointer"
                      style={{ background: "#1e2023", border: "1px solid #554337", color: currentPriority.color }}
                    >
                      {PRIORITY_OPTIONS.map(p => (
                        <option key={p.value} value={p.value} style={{ color: p.color, background: "#1e2023" }}>{p.label}</option>
                      ))}
                    </select>
                    <span
                      className="absolute left-4 top-1/2 -translate-y-1/2 text-[13px] font-bold pointer-events-none"
                      style={{ color: currentPriority.color }}
                    >
                      {currentPriority.icon}
                    </span>
                    <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[16px] pointer-events-none">
                      expand_more
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Bloque info Owner — solo en creación */}
            {isCreate && (
              <div
                className="flex items-start gap-4 rounded-xl p-4"
                style={{ background: "rgba(255,183,134,0.06)", border: "1px solid rgba(255,183,134,0.2)" }}
              >
                <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: "rgba(255,183,134,0.15)" }}>
                  <span className="material-symbols-outlined text-primary text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>info</span>
                </div>
                <p className="text-on-surface-variant text-sm leading-relaxed">
                  Al crear este proyecto, serás asignado automáticamente como{" "}
                  <span className="text-primary font-semibold">Owner</span> del mismo. Esto te otorgará permisos totales de edición y gestión.
                </p>
              </div>
            )}

            {/* Error API */}
            {error && (
              <div className="flex items-start gap-3 rounded-xl px-4 py-3" style={{ background: "rgba(255,180,171,0.1)", border: "1px solid rgba(255,180,171,0.3)" }}>
                <span className="material-symbols-outlined text-error text-[18px] flex-shrink-0 mt-0.5">error</span>
                <p className="text-error text-sm leading-relaxed">{error}</p>
              </div>
            )}

            {/* Zona de peligro — solo en edición */}
            {!isCreate && (
              <div className="rounded-xl p-4 flex flex-col gap-3" style={{ background: "rgba(255,180,171,0.06)", border: "1px solid rgba(255,180,171,0.2)" }}>
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-error text-[18px]">warning</span>
                  <span className="text-error text-sm font-semibold">Zona de peligro</span>
                </div>
                <p className="text-on-surface-variant text-xs leading-relaxed">
                  Al eliminar este proyecto, todos los datos, tareas asociadas y documentos adjuntos se perderán de forma permanente. Esta acción no se puede deshacer.
                </p>
                {onDelete && (
                  <button
                    type="button"
                    onClick={() => { handleClose(); setTimeout(onDelete, 350); }}
                    className="w-full py-2.5 rounded-full text-sm font-semibold transition-all hover:opacity-90 mt-1"
                    style={{ background: "rgba(147,0,10,0.4)", color: "#ffb4ab", border: "1px solid rgba(255,180,171,0.3)" }}
                  >
                    Eliminar proyecto
                  </button>
                )}
              </div>
            )}

            {/* Imagen decorativa — solo en creación */}
            {isCreate && (
              <div className="rounded-xl overflow-hidden flex-shrink-0" style={{ border: "1px solid #2D3135" }}>
                <div className="h-32 flex items-center justify-center" style={{ background: "linear-gradient(135deg, #1a1c1f 0%, #0c0e11 50%, #1a1c1f 100%)" }}>
                  <div className="flex flex-col items-center gap-2 opacity-25">
                    <span className="material-symbols-outlined text-primary text-[40px]">dashboard_customize</span>
                    <span className="text-on-surface-variant text-xs font-medium tracking-wider uppercase">Struktura Workspace</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer fijo */}
          <div
            className="flex items-center gap-3 px-6 py-4 flex-shrink-0 border-t"
            style={{ borderColor: "#2D3135" }}
          >
            <button
              type="button"
              onClick={handleClose}
              disabled={loading}
              className="flex-1 py-3 rounded-full text-sm font-semibold transition-all disabled:opacity-50 hover:opacity-80"
              style={
                isCreate
                  ? { color: "#4cd7f2", border: "1px solid #4cd7f2" }
                  : { background: "#1e2023", color: "#e2e2e6", border: "1px solid #2D3135" }
              }
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-full text-sm font-bold transition-all disabled:opacity-50 hover:opacity-90 active:scale-95"
              style={{ background: "#da7726", color: "#fff", boxShadow: "0 4px 16px rgba(218,119,38,0.35)" }}
            >
              {loading && (
                <span className="w-4 h-4 rounded-full border-2 flex-shrink-0"
                  style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "#fff", animation: "spin 1s linear infinite" }} />
              )}
              {loading ? (isCreate ? "Creando…" : "Guardando…") : (isCreate ? "Crear proyecto" : "Guardar cambios")}
            </button>
          </div>
        </form>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  );
}

// ── DeleteConfirmModal ─────────────────────────────────────────────────────────

export function DeleteConfirmModal({ project, loading, error, blockingTasks = [], onConfirm, onClose }) {
  const [confirmText, setConfirmText] = useState("");
  const inputRef = useRef(null);

  const projectName = project?.name ?? "";
  const nameMatches = confirmText === projectName;
  const hasBlockers = blockingTasks.length > 0;
  const canConfirm  = nameMatches && !hasBlockers && !loading;

  useEffect(() => {
    const h = (e) => { if (e.key === "Escape" && !loading) onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose, loading]);

  useEffect(() => {
    setTimeout(() => inputRef.current?.focus(), 100);
  }, []);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[100]"
        style={{ backdropFilter: "blur(12px)", background: "rgba(15,17,19,0.7)" }}
        onClick={() => !loading && onClose()}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-[101] flex items-center justify-center p-4">
        <div
          className="w-full max-w-[520px] rounded-xl flex flex-col overflow-hidden shadow-2xl"
          style={{ background: "#282a2d", border: "1px solid rgba(85,67,55,0.4)" }}
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div
            className="flex items-start gap-4 p-6 border-b"
            style={{ borderColor: "rgba(85,67,55,0.3)" }}
          >
            <div className="p-2 rounded-lg flex-shrink-0" style={{ background: "rgba(147,0,10,0.2)" }}>
              <span
                className="material-symbols-outlined text-error text-[32px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                warning
              </span>
            </div>
            <div className="flex-1 pt-1">
              <h2 className="font-['Poppins'] font-semibold text-on-surface text-xl leading-tight">
                ¿Eliminar proyecto permanentemente?
              </h2>
              <p className="text-error text-xs font-medium uppercase tracking-widest mt-1 opacity-80">
                Acción Irreversible
              </p>
            </div>
          </div>

          {/* Cuerpo */}
          <div className="p-6 flex flex-col gap-5">
            <div
              className="p-4 rounded-lg border-l-4"
              style={{ background: "rgba(147,0,10,0.1)", borderLeftColor: "#ffb4ab" }}
            >
              <p className="text-on-surface text-sm leading-relaxed">
                Estás a punto de eliminar el proyecto{" "}
                <span className="font-bold text-primary">{projectName}</span>.
                Esta acción borrará permanentemente todas las tareas, documentos,
                historiales y archivos asociados.
              </p>
            </div>

            {/* Tareas bloqueantes */}
            {hasBlockers && (
              <div
                className="rounded-xl p-4 flex flex-col gap-3"
                style={{ background: "rgba(255,180,171,0.08)", border: "1px solid rgba(255,180,171,0.25)" }}
              >
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-error text-[18px]">block</span>
                  <p className="text-error text-sm font-semibold">No se puede eliminar — tareas activas</p>
                </div>
                <p className="text-on-surface-variant text-xs leading-relaxed">
                  Completa o elimina las siguientes tareas antes de continuar:
                </p>
                <ul className="flex flex-col gap-1.5">
                  {blockingTasks.map((task, i) => (
                    <li key={i} className="flex items-center gap-2 text-xs text-on-surface-variant">
                      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "#ffb4ab" }} />
                      {task}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Error genérico */}
            {error && !hasBlockers && (
              <div
                className="flex items-start gap-3 px-4 py-3 rounded-xl"
                style={{ background: "rgba(255,180,171,0.1)", border: "1px solid rgba(255,180,171,0.3)" }}
              >
                <span className="material-symbols-outlined text-error text-[16px] flex-shrink-0 mt-0.5">error</span>
                <p className="text-error text-sm">{error}</p>
              </div>
            )}

            {/* Input confirmación */}
            {!hasBlockers && (
              <div className="flex flex-col gap-2">
                <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest">
                  Escribe el nombre del proyecto para confirmar:
                </label>
                <div className="relative">
                  <input
                    ref={inputRef}
                    type="text"
                    value={confirmText}
                    onChange={e => setConfirmText(e.target.value)}
                    placeholder={projectName}
                    disabled={loading}
                    autoComplete="off"
                    className="w-full rounded-xl px-4 py-3 pr-12 text-sm text-on-surface placeholder:text-on-surface-variant/30 focus:outline-none transition-all disabled:opacity-50"
                    style={{
                      background: "#0c0e11",
                      border: nameMatches
                        ? "1px solid #4cd7f2"
                        : confirmText
                        ? "1px solid #554337"
                        : "1px solid rgba(85,67,55,0.4)",
                      boxShadow: nameMatches ? "0 0 0 4px rgba(76,215,242,0.15)" : "none",
                    }}
                    onKeyDown={e => { if (e.key === "Enter" && canConfirm) onConfirm(); }}
                  />
                  <div
                    className="absolute right-4 top-1/2 -translate-y-1/2 transition-all duration-200"
                    style={{ opacity: nameMatches ? 1 : 0, transform: `translateY(-50%) scale(${nameMatches ? 1 : 0.5})` }}
                  >
                    <span
                      className="material-symbols-outlined text-secondary text-[22px]"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      check_circle
                    </span>
                  </div>
                </div>
                {confirmText && !nameMatches && (
                  <p className="text-on-surface-variant text-xs opacity-60">El nombre no coincide exactamente</p>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div
            className="flex flex-col sm:flex-row-reverse gap-3 px-6 py-4 border-t"
            style={{ background: "rgba(51,53,56,0.3)", borderColor: "rgba(85,67,55,0.3)" }}
          >
            <button
              onClick={onConfirm}
              disabled={!canConfirm}
              className="flex items-center justify-center gap-2 px-6 py-3 rounded-full text-sm font-semibold transition-all active:scale-95"
              style={{
                background: canConfirm ? "#ffb4ab" : "rgba(255,180,171,0.2)",
                color: canConfirm ? "#690005" : "rgba(255,180,171,0.4)",
                cursor: canConfirm ? "pointer" : "not-allowed",
                boxShadow: canConfirm ? "0 4px 16px rgba(255,180,171,0.2)" : "none",
              }}
            >
              {loading ? (
                <>
                  <span
                    className="w-4 h-4 rounded-full border-2 flex-shrink-0"
                    style={{ borderColor: "rgba(105,0,5,0.3)", borderTopColor: "#690005", animation: "spin 1s linear infinite" }}
                  />
                  Eliminando…
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[18px]">delete_forever</span>
                  Eliminar permanentemente
                </>
              )}
            </button>
            <button
              onClick={onClose}
              disabled={loading}
              className="px-6 py-3 rounded-full text-sm font-medium text-on-surface transition-all disabled:opacity-50 hover:bg-surface-variant active:scale-95"
            >
              Cancelar
            </button>
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  );
}

// ── Utilidad ───────────────────────────────────────────────────────────────────

function formatRelative(isoString) {
  if (!isoString) return "—";
  const date = new Date(isoString);
  const now  = new Date();
  const diff = Math.floor((now - date) / 1000);
  if (diff < 60)       return "Justo ahora";
  if (diff < 3600)     return `Hace ${Math.floor(diff / 60)} min`;
  if (diff < 86400)    return `Hace ${Math.floor(diff / 3600)} h`;
  if (diff < 2592000)  return `Hace ${Math.floor(diff / 86400)} días`;
  if (diff < 31536000) return `Hace ${Math.floor(diff / 2592000)} meses`;
  return `Hace ${Math.floor(diff / 31536000)} años`;
}