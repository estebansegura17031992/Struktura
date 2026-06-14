/**
 * MemberComponents.jsx
 * Componentes — Panel de Miembros del Proyecto
 * Sprint 2 · E03 · R-0304 · R-0305
 *
 * Exporta:
 *   MemberRow            — fila de miembro activo con rol y acciones
 *   HistoryRow           — fila de miembro removido (historial)
 *   MemberSkeleton       — skeleton de carga
 *   RemoveMemberModal    — confirmación de remoción con alerta de timer activo
 *   TransferOwnerModal   — selector de nuevo owner + confirmación por username
 */
import React, { useState, useEffect, useRef, useCallback } from "react";

// ── Constantes ────────────────────────────────────────────────────────────────

const ROLE_META = {
  owner:  { label: "Owner",  color: "#ffb786", bg: "rgba(255,183,134,0.15)", border: "rgba(255,183,134,0.3)", icon: "workspace_premium" },
  editor: { label: "Editor", color: "#a78bfa", bg: "rgba(167,139,250,0.15)", border: "rgba(167,139,250,0.3)", icon: "edit" },
  viewer: { label: "Viewer", color: "#94a3b8", bg: "rgba(148,163,184,0.12)", border: "rgba(148,163,184,0.25)", icon: "visibility" },
  admin:  { label: "Admin",  color: "#fbbf24", bg: "rgba(251,191,36,0.12)",  border: "rgba(251,191,36,0.25)",  icon: "shield" },
};

function RoleChip({ role }) {
  const m = ROLE_META[role?.toLowerCase()] ?? ROLE_META.viewer;
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1 rounded-full"
      style={{ color: m.color, background: m.bg, border: `1px solid ${m.border}` }}
    >
      <span className="material-symbols-outlined text-[13px]" style={{ fontVariationSettings: "'FILL' 1" }}>
        {m.icon}
      </span>
      {m.label}
    </span>
  );
}

function MemberAvatar({ name, username, isSelf = false, isOnline = false }) {
  const initials = (name ?? username ?? "?").split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
  const colors = ["#da7726","#4cd7f2","#a78bfa","#f6ba8b"];
  const bg = colors[(name?.charCodeAt(0) ?? 0) % colors.length];
  return (
    <div className="relative flex-shrink-0">
      <div
        className="w-12 h-12 rounded-full flex items-center justify-center font-bold text-sm"
        style={{
          background: bg + "30",
          color: bg,
          border: isSelf ? `2px solid ${bg}` : "2px solid rgba(85,67,55,0.3)",
        }}
      >
        {initials}
      </div>
      {isOnline && (
        <div
          className="absolute bottom-0.5 right-0.5 w-3 h-3 rounded-full border-2"
          style={{ background: "#4ade80", borderColor: "#111316" }}
        />
      )}
    </div>
  );
}

// ── MemberRow ──────────────────────────────────────────────────────────────────

export function MemberRow({ member, currentUserId, myRole, onRemove }) {
  const isSelf   = member.user_id === currentUserId;
  const isOwner  = member.role === "owner";
  const canRemove = (myRole === "owner" || myRole === "admin") && !isSelf && !isOwner;

  const displayName = member.user?.full_name || member.user?.username || `Usuario ${member.user_id?.slice(0, 8)}`;
  const username    = member.user?.username ?? "";
  const taskCount   = member.task_count ?? 0;
  const joinedAgo   = formatRelative(member.joined_at);

  return (
    <div
      className="flex items-center gap-4 px-5 py-4 rounded-xl transition-colors"
      style={{
        background: isSelf ? "rgba(255,183,134,0.05)" : "#1a1c1f",
        border: `1px solid ${isSelf ? "rgba(255,183,134,0.2)" : "#2D3135"}`,
      }}
    >
      {/* Avatar */}
      <MemberAvatar name={displayName} username={username} isSelf={isSelf} isOnline={member.has_active_timer} />

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="font-semibold text-on-surface text-sm">{displayName}</span>
          {isSelf && (
            <span
              className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase"
              style={{ background: "rgba(76,215,242,0.15)", color: "#4cd7f2" }}
            >
              TÚ
            </span>
          )}
        </div>
        <span className="text-on-surface-variant text-xs font-mono">@{username}</span>
      </div>

      {/* Rol */}
      <div className="hidden sm:block w-28 text-center">
        <span className="text-on-surface-variant text-[10px] uppercase tracking-wider block mb-1">Rol</span>
        <RoleChip role={member.role} />
      </div>

      {/* Actividad */}
      <div className="hidden md:block w-36 text-center">
        <span className="text-on-surface-variant text-[10px] uppercase tracking-wider block mb-1">Actividad</span>
        <span className="text-on-surface text-xs">{taskCount} tareas asignadas</span>
      </div>

      {/* Membresía */}
      <div className="hidden md:block w-32 text-center">
        <span className="text-on-surface-variant text-[10px] uppercase tracking-wider block mb-1">Membresía</span>
        <span className="text-on-surface-variant text-xs">{joinedAgo}</span>
      </div>

      {/* Acciones */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {isSelf && myRole === "owner" && (
          <button
            onClick={() => {}}
            className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-colors"
            style={{ background: "#1e2023" }}
            title="Configuración"
          >
            <span className="material-symbols-outlined text-[18px]">settings</span>
          </button>
        )}
        {canRemove && (
          <button
            onClick={() => onRemove(member)}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-semibold transition-all hover:opacity-90"
            style={{ background: "rgba(255,180,171,0.12)", color: "#ffb4ab", border: "1px solid rgba(255,180,171,0.25)" }}
          >
            Remover
          </button>
        )}
      </div>
    </div>
  );
}

// ── HistoryRow ─────────────────────────────────────────────────────────────────

export function HistoryRow({ member }) {
  const displayName = member.user?.full_name || member.user?.username || `Usuario ${member.user_id?.slice(0, 8)}`;
  const username    = member.user?.username ?? "";

  return (
    <div
      className="flex items-center gap-4 px-5 py-3 rounded-xl opacity-60"
      style={{ background: "#1a1c1f", border: "1px solid #2D3135" }}
    >
      <div className="relative flex-shrink-0">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold grayscale"
          style={{ background: "#333538", color: "#94a3b8", border: "2px solid #2D3135" }}
        >
          {(displayName[0] ?? "?").toUpperCase()}
        </div>
        <div
          className="absolute -bottom-0.5 -right-0.5 w-5 h-5 rounded-full flex items-center justify-center"
          style={{ background: "#93000a", border: "2px solid #111316" }}
        >
          <span className="material-symbols-outlined text-[10px] text-on-error">close</span>
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <span className="font-medium text-on-surface-variant text-sm line-through">{displayName}</span>
        <div className="text-on-surface-variant text-xs font-mono opacity-70">@{username}</div>
      </div>
      <div className="hidden sm:flex items-center gap-2">
        <RoleChip role={member.role} />
      </div>
      <div className="text-on-surface-variant text-xs text-right flex-shrink-0">
        <div>Removido</div>
        <div className="opacity-70">{formatRelative(member.removed_at)}</div>
      </div>
    </div>
  );
}

// ── Skeleton ───────────────────────────────────────────────────────────────────

export function MemberSkeleton() {
  return (
    <div
      className="flex items-center gap-4 px-5 py-4 rounded-xl animate-pulse"
      style={{ background: "#1a1c1f", border: "1px solid #2D3135" }}
    >
      <div className="w-12 h-12 rounded-full bg-surface-variant/50 flex-shrink-0" />
      <div className="flex-1 flex flex-col gap-2">
        <div className="h-4 bg-surface-variant/50 rounded-full w-36" />
        <div className="h-3 bg-surface-variant/30 rounded-full w-24" />
      </div>
      <div className="w-20 h-6 bg-surface-variant/40 rounded-full hidden sm:block" />
      <div className="w-28 h-4 bg-surface-variant/30 rounded-full hidden md:block" />
      <div className="w-24 h-4 bg-surface-variant/30 rounded-full hidden md:block" />
    </div>
  );
}

// ── RemoveMemberModal ──────────────────────────────────────────────────────────
// Wireframe 2: ícono person_remove + badge X rojo · bloque info · alerta timer activo

export function RemoveMemberModal({ member, loading, error, onConfirm, onClose }) {
  const displayName = member?.user?.full_name || member?.user?.username || "este miembro";
  const hasTimer    = member?.has_active_timer ?? false;

  useEffect(() => {
    const h = (e) => { if (e.key === "Escape" && !loading) onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose, loading]);

  return (
    <>
      <div
        className="fixed inset-0 z-40"
        style={{ backdropFilter: "blur(12px)", background: "rgba(15,17,19,0.85)" }}
        onClick={() => !loading && onClose()}
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="w-full max-w-[440px] rounded-xl overflow-hidden shadow-2xl"
          style={{ background: "#1e2023", border: "1px solid rgba(85,67,55,0.4)" }}
          onClick={e => e.stopPropagation()}
        >
          {/* Header centrado */}
          <div className="px-6 pt-8 pb-4 flex flex-col items-center text-center gap-4">
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center relative"
              style={{ background: "rgba(147,0,10,0.2)" }}
            >
              <span
                className="material-symbols-outlined text-error text-[32px]"
                style={{ fontVariationSettings: "'FILL' 0" }}
              >
                person_remove
              </span>
              <div
                className="absolute -top-1 -right-1 w-6 h-6 rounded-full flex items-center justify-center border-4"
                style={{ background: "#ffb4ab", borderColor: "#1e2023" }}
              >
                <span className="material-symbols-outlined text-[12px] text-on-error font-bold">close</span>
              </div>
            </div>
            <h2 className="font-['Poppins'] font-bold text-on-surface text-xl max-w-[300px] leading-tight">
              Remover a {displayName} del proyecto
            </h2>
          </div>

          {/* Cuerpo */}
          <div className="px-6 pb-5 flex flex-col gap-4">
            {/* Bloque info */}
            <div
              className="p-4 rounded-xl"
              style={{ background: "rgba(51,53,56,0.5)", border: "1px solid rgba(85,67,55,0.3)" }}
            >
              <p className="text-on-surface-variant text-sm leading-relaxed text-center">
                Esta acción revocará el acceso de{" "}
                <span className="text-on-surface font-medium">{displayName.split(" ")[0]}</span> de
                forma inmediata. Las{" "}
                <span className="text-on-surface font-medium">tareas asignadas</span> y el{" "}
                <span className="text-on-surface font-medium">historial de tiempo</span> se
                conservarán íntegros para garantizar la trazabilidad del proyecto.
              </p>
            </div>

            {/* Alerta timer activo — condicional */}
            {hasTimer && (
              <div
                className="flex items-start gap-3 p-4 rounded-xl"
                style={{ background: "rgba(255,183,134,0.08)", border: "1px solid rgba(255,183,134,0.25)" }}
              >
                <span
                  className="material-symbols-outlined text-primary text-[22px] flex-shrink-0 mt-0.5"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  timer
                </span>
                <div>
                  <p className="text-primary text-sm font-semibold mb-1">Temporizador activo detectado</p>
                  <p className="text-on-surface-variant text-xs leading-relaxed">
                    {displayName.split(" ")[0]} tiene un temporizador en curso que se{" "}
                    <span className="text-on-surface font-semibold">detendrá automáticamente</span> y el
                    tiempo transcurrido será guardado antes de la remoción.
                  </p>
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div
                className="flex items-start gap-2 px-4 py-3 rounded-xl"
                style={{ background: "rgba(255,180,171,0.1)", border: "1px solid rgba(255,180,171,0.3)" }}
              >
                <span className="material-symbols-outlined text-error text-[16px] flex-shrink-0 mt-0.5">error</span>
                <p className="text-error text-sm">{error}</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div
            className="flex gap-3 px-6 py-4 border-t"
            style={{ background: "rgba(51,53,56,0.3)", borderColor: "rgba(85,67,55,0.3)" }}
          >
            <button
              onClick={onClose}
              disabled={loading}
              className="flex-1 py-3 rounded-full text-sm font-semibold text-on-surface-variant transition-all hover:bg-surface-variant disabled:opacity-50"
              style={{ border: "1px solid #a38c7e" }}
            >
              Cancelar
            </button>
            <button
              onClick={onConfirm}
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-full text-sm font-bold transition-all hover:opacity-90 active:scale-95 disabled:opacity-50"
              style={{ background: "#ffb4ab", color: "#690005" }}
            >
              {loading && (
                <span
                  className="w-4 h-4 rounded-full border-2 flex-shrink-0"
                  style={{ borderColor: "rgba(105,0,5,0.3)", borderTopColor: "#690005", animation: "spin 1s linear infinite" }}
                />
              )}
              {loading ? "Removiendo…" : "Remover del proyecto"}
            </button>
          </div>
        </div>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  );
}

// ── TransferOwnerModal ─────────────────────────────────────────────────────────
// Wireframe 3: advertencia · búsqueda de miembro · confirmación por @username

export function TransferOwnerModal({ members, currentUserId, loading, error, onConfirm, onClose }) {
  const [search, setSearch]           = useState("");
  const [selected, setSelected]       = useState(null);
  const [confirmText, setConfirmText] = useState("");
  const searchRef = useRef(null);

  useEffect(() => {
    setTimeout(() => searchRef.current?.focus(), 100);
  }, []);

  useEffect(() => {
    const h = (e) => { if (e.key === "Escape" && !loading) onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose, loading]);

  // Candidatos: miembros activos que no son el usuario actual ni el owner actual
  const candidates = members.filter(m =>
    m.user_id !== currentUserId &&
    m.role !== "owner" &&
    m.is_active !== false
  );

  const filtered = search.trim()
    ? candidates.filter(m => {
        const name = (m.user?.full_name ?? "").toLowerCase();
        const uname = (m.user?.username ?? "").toLowerCase();
        const q = search.toLowerCase();
        return name.includes(q) || uname.includes(q);
      })
    : candidates;

  const selectedUsername = selected?.user?.username ?? "";
  const confirmMatch     = confirmText === `@${selectedUsername}`;
  const canTransfer      = selected && confirmMatch && !loading;

  const handleConfirm = () => {
    if (canTransfer) onConfirm(selected.user_id);
  };

  return (
    <>
      <div
        className="fixed inset-0 z-40"
        style={{ backdropFilter: "blur(12px)", background: "rgba(15,17,19,0.85)" }}
        onClick={() => !loading && onClose()}
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="w-full max-w-[520px] rounded-xl overflow-hidden shadow-2xl flex flex-col"
          style={{ background: "#1e2023", border: "1px solid rgba(85,67,55,0.4)", maxHeight: "90vh" }}
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between px-6 py-5 border-b"
            style={{ borderColor: "rgba(85,67,55,0.3)" }}
          >
            <div className="flex items-center gap-3">
              <span
                className="material-symbols-outlined text-primary text-[22px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                workspace_premium
              </span>
              <h2 className="font-['Poppins'] font-semibold text-on-surface text-xl">
                Transferir ownership
              </h2>
            </div>
            <button
              onClick={onClose}
              disabled={loading}
              className="w-8 h-8 rounded-full flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-colors disabled:opacity-50"
              onMouseEnter={e => e.currentTarget.style.background = "#333538"}
              onMouseLeave={e => e.currentTarget.style.background = "transparent"}
            >
              <span className="material-symbols-outlined text-[20px]">close</span>
            </button>
          </div>

          {/* Cuerpo scrollable */}
          <div className="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-5">

            {/* Advertencia */}
            <div
              className="flex items-start gap-3 p-4 rounded-xl"
              style={{ background: "rgba(255,183,134,0.08)", border: "1px solid rgba(255,183,134,0.25)" }}
            >
              <span className="material-symbols-outlined text-primary text-[20px] flex-shrink-0 mt-0.5">warning</span>
              <p className="text-on-surface-variant text-sm leading-relaxed">
                Una vez transferido, dejarás de ser el owner de este proyecto y pasarás a tener
                rol de <span className="text-primary font-semibold">Editor</span>. Esta acción no
                puede deshacerse desde aquí.
              </p>
            </div>

            {/* Seleccionar nuevo owner */}
            <div>
              <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest block mb-3">
                Seleccionar nuevo owner
              </label>

              {/* Búsqueda */}
              <div className="relative mb-3">
                <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">
                  search
                </span>
                <input
                  ref={searchRef}
                  type="text"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Buscar por nombre o username..."
                  className="w-full rounded-xl pl-11 pr-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none transition-all"
                  style={{
                    background: "#111316",
                    border: "1px solid #554337",
                  }}
                  onFocus={e => e.target.style.borderColor = "#4cd7f2"}
                  onBlur={e => e.target.style.borderColor = "#554337"}
                />
              </div>

              {/* Lista de candidatos */}
              <div
                className="rounded-xl overflow-hidden flex flex-col"
                style={{ border: "1px solid #2D3135", maxHeight: 220, overflowY: "auto" }}
              >
                {filtered.length === 0 ? (
                  <div className="py-8 flex flex-col items-center gap-2 text-on-surface-variant">
                    <span className="material-symbols-outlined text-[28px] opacity-30">group_off</span>
                    <p className="text-xs">No hay miembros disponibles</p>
                  </div>
                ) : (
                  filtered.map(m => {
                    const name    = m.user?.full_name || m.user?.username || "Miembro";
                    const uname   = m.user?.username ?? "";
                    const isSelected = selected?.user_id === m.user_id;
                    return (
                      <button
                        key={m.user_id}
                        onClick={() => { setSelected(m); setConfirmText(""); }}
                        className="flex items-center gap-3 px-4 py-3 text-left transition-colors"
                        style={{
                          background: isSelected ? "rgba(255,183,134,0.1)" : "transparent",
                          borderBottom: "1px solid #2D3135",
                        }}
                        onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = "#282a2d"; }}
                        onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}
                      >
                        <div
                          className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                          style={{ background: "#333538", color: "#dcc1b2" }}
                        >
                          {name[0]?.toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-on-surface text-sm font-medium">{name}</p>
                          <p className="text-on-surface-variant text-xs font-mono">@{uname}</p>
                        </div>
                        <span
                          className="text-[10px] font-bold px-2 py-0.5 rounded uppercase"
                          style={{
                            background: ROLE_META[m.role]?.bg ?? "#333538",
                            color: ROLE_META[m.role]?.color ?? "#94a3b8",
                          }}
                        >
                          {m.role}
                        </span>
                        {isSelected && (
                          <span
                            className="material-symbols-outlined text-[18px] flex-shrink-0"
                            style={{ color: "#ffb786", fontVariationSettings: "'FILL' 1" }}
                          >
                            check_circle
                          </span>
                        )}
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            {/* Confirmación por @username */}
            {selected && (
              <div>
                <label className="text-on-surface-variant text-xs font-medium uppercase tracking-widest block mb-1">
                  Confirmar transferencia
                </label>
                <p className="text-on-surface-variant text-xs mb-3">
                  Escribe{" "}
                  <code
                    className="px-1.5 py-0.5 rounded text-primary font-bold"
                    style={{ background: "rgba(255,183,134,0.15)" }}
                  >
                    @{selectedUsername}
                  </code>{" "}
                  para confirmar.
                </p>
                <div className="relative">
                  <input
                    type="text"
                    value={confirmText}
                    onChange={e => setConfirmText(e.target.value)}
                    placeholder={`Escribe el username aquí`}
                    className="w-full rounded-xl px-4 py-3 pr-12 text-sm font-mono text-on-surface placeholder:text-on-surface-variant/30 focus:outline-none transition-all"
                    style={{
                      background: "#111316",
                      border: confirmMatch ? "1px solid #4cd7f2" : "1px solid #554337",
                      boxShadow: confirmMatch ? "0 0 0 4px rgba(76,215,242,0.12)" : "none",
                    }}
                    onKeyDown={e => { if (e.key === "Enter" && canTransfer) handleConfirm(); }}
                  />
                  {confirmMatch && (
                    <span
                      className="absolute right-4 top-1/2 -translate-y-1/2 material-symbols-outlined text-secondary text-[22px]"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      check_circle
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div
                className="flex items-start gap-3 px-4 py-3 rounded-xl"
                style={{ background: "rgba(255,180,171,0.1)", border: "1px solid rgba(255,180,171,0.3)" }}
              >
                <span className="material-symbols-outlined text-error text-[16px] flex-shrink-0 mt-0.5">error</span>
                <p className="text-error text-sm">{error}</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div
            className="flex gap-3 px-6 py-4 border-t"
            style={{ background: "rgba(51,53,56,0.3)", borderColor: "rgba(85,67,55,0.3)" }}
          >
            <button
              onClick={onClose}
              disabled={loading}
              className="flex-1 py-3 rounded-full text-sm font-semibold text-on-surface-variant transition-all hover:bg-surface-variant disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              onClick={handleConfirm}
              disabled={!canTransfer}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-full text-sm font-bold transition-all active:scale-95"
              style={{
                background: canTransfer ? "#ffb4ab" : "rgba(255,180,171,0.15)",
                color: canTransfer ? "#690005" : "rgba(255,180,171,0.4)",
                cursor: canTransfer ? "pointer" : "not-allowed",
              }}
            >
              {loading && (
                <span
                  className="w-4 h-4 rounded-full border-2 flex-shrink-0"
                  style={{ borderColor: "rgba(105,0,5,0.3)", borderTopColor: "#690005", animation: "spin 1s linear infinite" }}
                />
              )}
              <span className="material-symbols-outlined text-[16px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                workspace_premium
              </span>
              {loading ? "Transfiriendo…" : "Transferir ownership"}
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
  const diff = Math.floor((Date.now() - new Date(isoString)) / 1000);
  if (diff < 60)       return "Justo ahora";
  if (diff < 3600)     return `Hace ${Math.floor(diff / 60)} min`;
  if (diff < 86400)    return `Hace ${Math.floor(diff / 3600)} h`;
  if (diff < 2592000)  return `Hace ${Math.floor(diff / 86400)} días`;
  if (diff < 31536000) return `Hace ${Math.floor(diff / 2592000)} meses`;
  return `Hace ${Math.floor(diff / 31536000)} años`;
}