/**
 * ProjectMembersPage.jsx
 * Página: Panel de Miembros del Proyecto
 * Sprint 2 · E03 · R-0304 · R-0305
 *
 * Fix: obtiene my_role y projectName desde GET /projects/{id}
 * para no depender de props cuando se accede por URL directa.
 */
import React, { useState, useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { logoutUser } from "@/api/auth";
import api from "@/api/axiosInstance";
import { useMembers } from "@/hooks/useMembers";
import {
  MemberRow, HistoryRow, MemberSkeleton,
  RemoveMemberModal, TransferOwnerModal,
} from "@/components/members/MemberComponents";

// ── Sidebar nav ────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { icon: "dashboard",            label: "Dashboard",      path: "/dashboard" },
  { icon: "folder_managed",       label: "Proyectos",      path: "/projects",     active: true },
  { icon: "assignment",           label: "Tareas",         path: "/tasks" },
  { icon: "group",                label: "Equipo",         path: "/team" },
  { icon: "admin_panel_settings", label: "Administración", path: "/admin/users" },
];

export default function ProjectMembersPage({ projectId: propProjectId, projectName: propName, myRole: propRole }) {
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();
  const params   = useParams();
  const projectId = propProjectId ?? params.projectId;

  // ── Carga del proyecto para obtener my_role y nombre ──────────────────────
  const [project, setProject]       = useState(null);
  const [projectLoading, setProjectLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    setProjectLoading(true);
    api.get(`/projects/${projectId}`)
      .then(r => setProject(r.data))
      .catch(() => {})
      .finally(() => setProjectLoading(false));
  }, [projectId]);

  // Rol resuelto: prop directa → campo del proyecto → rol global del usuario
  const resolvedRole = propRole ?? project?.my_role ?? user?.role;
  const resolvedName = propName ?? project?.name ?? "Proyecto";
  const isOwner      = resolvedRole === "owner" || user?.role === "admin";

  // ── Hook de miembros ───────────────────────────────────────────────────────
  const {
    members, loading, error, refresh,
    historyOpen, toggleHistory,
    history, historyLoading, historyTotal,
    removingMember, openRemove, closeRemove,
    removing, removeError, confirmRemove,
    showTransfer, openTransfer, closeTransfer,
    transferring, transferError, confirmTransfer,
  } = useMembers(projectId);

  const handleLogout = async () => {
    try { await logoutUser(); } catch {}
    clearAuth();
    navigate("/login");
  };

  const initials = user?.full_name
    ? user.full_name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2)
    : user?.username?.slice(0, 2).toUpperCase() || "??";

  const totalCount = members.length;

  return (
    <div className="min-h-screen font-['Inter'] text-on-background" style={{ backgroundColor: "#111316" }}>

      {/* ── Header sticky ─────────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-50 border-b"
        style={{ backgroundColor: "#111316", borderColor: "#2D3135" }}
      >
        <div className="flex items-center justify-between px-6 py-3 gap-4">
          <Link to="/dashboard" className="font-['Poppins'] text-2xl font-bold text-primary flex-shrink-0">
            Struktura
          </Link>

          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm flex-shrink-0">
            <Link to="/projects" className="text-on-surface-variant hover:text-secondary transition-colors">
              Proyectos
            </Link>
            <span className="material-symbols-outlined text-on-surface-variant text-[14px]">chevron_right</span>
            <span className="text-on-surface font-medium">{resolvedName}</span>
          </div>

          <div className="flex-1" />

          <div className="flex items-center gap-3">
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

          <div className="px-3 pb-4 mt-auto">
            <Link
              to="/projects"
              className="w-full flex items-center justify-center gap-2 py-3 rounded-full font-semibold text-sm transition-opacity hover:opacity-90"
              style={{ background: "#da7726", color: "#461f00" }}
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
              Nuevo Proyecto
            </Link>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="p-6 flex-1 flex flex-col gap-6 max-w-4xl mx-auto w-full">

            {/* Título + CTA */}
            <div className="flex items-end justify-between gap-4 flex-wrap">
              <div>
                <h1 className="font-['Poppins'] text-3xl font-bold text-on-surface">
                  Miembros del proyecto{" "}
                  {!loading && <span className="text-primary">({totalCount})</span>}
                </h1>
                <p className="text-on-surface-variant text-sm mt-1">
                  Administra los permisos y accesos de tu equipo.
                </p>
              </div>
              <button
                disabled
                className="flex items-center gap-2 px-6 py-2.5 rounded-full text-sm font-semibold opacity-40 cursor-not-allowed"
                style={{ background: "#da7726", color: "#461f00" }}
                title="Disponible en Sprint 4"
              >
                <span className="material-symbols-outlined text-[18px]">person_add</span>
                Invitar miembro
              </button>
            </div>

            {/* Banner invitaciones — placeholder Sprint 4 */}
            <div
              className="flex items-center gap-4 px-5 py-4 rounded-xl"
              style={{ background: "#1a1c1f", border: "1px solid #2D3135" }}
            >
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ background: "rgba(76,215,242,0.12)" }}
              >
                <span className="material-symbols-outlined text-secondary text-[20px]">mail</span>
              </div>
              <div className="flex-1">
                <p className="text-on-surface text-sm font-medium">Invitaciones pendientes</p>
                <p className="text-on-surface-variant text-xs">
                  Las invitaciones por email estarán disponibles en Sprint 4.
                </p>
              </div>
              <button className="text-on-surface-variant hover:text-on-surface transition-colors" aria-label="Cerrar">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            {/* Error */}
            {error && (
              <div
                className="px-5 py-4 rounded-xl flex items-center gap-3"
                style={{ background: "rgba(255,180,171,0.1)", border: "1px solid rgba(255,180,171,0.3)" }}
              >
                <span className="material-symbols-outlined text-error">error</span>
                <span className="text-error text-sm flex-1">{error}</span>
                <button onClick={refresh} className="text-error text-sm font-bold underline">Reintentar</button>
              </div>
            )}

            {/* Cabecera tabla */}
            <div className="flex flex-col gap-2">
              <div className="grid grid-cols-12 px-5 py-2 text-on-surface-variant text-[10px] uppercase tracking-widest font-medium">
                <div className="col-span-4">Usuario</div>
                <div className="col-span-2 text-center hidden sm:block">Rol</div>
                <div className="col-span-3 text-center hidden md:block">Actividad</div>
                <div className="col-span-2 text-center hidden md:block">Membresía</div>
                <div className="col-span-1" />
              </div>

              {loading || projectLoading
                ? Array.from({ length: 4 }).map((_, i) => <MemberSkeleton key={i} />)
                : members.map(m => (
                    <MemberRow
                      key={m.id}
                      member={m}
                      currentUserId={user?.id}
                      myRole={resolvedRole}
                      onRemove={openRemove}
                    />
                  ))
              }
            </div>

            {/* Botón transferir ownership */}
            {isOwner && !loading && !projectLoading && (
              <div className="flex justify-end">
                <button
                  onClick={openTransfer}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition-all hover:opacity-90"
                  style={{
                    background: "rgba(255,183,134,0.1)",
                    color: "#ffb786",
                    border: "1px solid rgba(255,183,134,0.3)",
                  }}
                >
                  <span
                    className="material-symbols-outlined text-[18px]"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    workspace_premium
                  </span>
                  Transferir ownership
                </button>
              </div>
            )}

            {/* Historial colapsable */}
            <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #2D3135" }}>
              <button
                onClick={toggleHistory}
                className="w-full flex items-center justify-between px-5 py-4 transition-colors hover:bg-surface-container"
                style={{ background: "#1a1c1f" }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="material-symbols-outlined text-[18px] text-on-surface-variant transition-transform"
                    style={{ transform: historyOpen ? "rotate(180deg)" : "rotate(0)" }}
                  >
                    expand_more
                  </span>
                  <span className="text-on-surface text-sm font-medium">
                    Miembros anteriores{" "}
                    {historyTotal > 0 && <span className="text-on-surface-variant">({historyTotal})</span>}
                  </span>
                </div>
                <span className="text-on-surface-variant text-xs hover:text-secondary transition-colors">
                  Historial de remociones
                </span>
              </button>

              {historyOpen && (
                <div className="flex flex-col gap-2 p-4 border-t" style={{ borderColor: "#2D3135" }}>
                  {historyLoading
                    ? Array.from({ length: 2 }).map((_, i) => <MemberSkeleton key={i} />)
                    : history.length === 0
                    ? (
                      <div className="py-8 flex flex-col items-center gap-2 text-on-surface-variant opacity-60">
                        <span className="material-symbols-outlined text-[28px]">history</span>
                        <p className="text-sm">Sin miembros removidos</p>
                      </div>
                    )
                    : history.map(m => <HistoryRow key={m.id} member={m} />)
                  }
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* ── Modales ─────────────────────────────────────────────────────────── */}
      {removingMember && (
        <RemoveMemberModal
          member={removingMember}
          loading={removing}
          error={removeError}
          onConfirm={confirmRemove}
          onClose={closeRemove}
        />
      )}

      {showTransfer && (
        <TransferOwnerModal
          members={members}
          currentUserId={user?.id}
          loading={transferring}
          error={transferError}
          onConfirm={confirmTransfer}
          onClose={closeTransfer}
        />
      )}
    </div>
  );
}