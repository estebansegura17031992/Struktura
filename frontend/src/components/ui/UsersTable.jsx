/**
 * UsersTable.jsx
 * Tabla principal de usuarios con soporte para loading, error, vacío
 */

import React from 'react';
import {
  Avatar, RoleSelect, EmailStatus, TimerStatus, SkeletonRow
} from './DesignSystem';
import { formatRelativeTime } from '../../lib/formatters';

export function UsersTable({ users, loading, currentUserId, onRequestRoleChange }) {

  return (
    <div className="bg-surface-container-low border border-outline-variant rounded-xl overflow-hidden relative">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse" aria-label="Lista de usuarios">
          <thead className="bg-surface-container text-on-surface-variant">
            <tr>
              <th className="px-6 py-4 font-label-lg text-label-lg text-xs uppercase tracking-wider whitespace-nowrap">Usuario</th>
              <th className="px-6 py-4 font-label-lg text-label-lg text-xs uppercase tracking-wider whitespace-nowrap">Email</th>
              <th className="px-6 py-4 font-label-lg text-label-lg text-xs uppercase tracking-wider">Rol</th>
              <th className="px-6 py-4 font-label-lg text-label-lg text-xs uppercase tracking-wider">Estado</th>
              <th className="px-6 py-4 font-label-lg text-label-lg text-xs uppercase tracking-wider whitespace-nowrap">Registro</th>
              <th className="px-6 py-4 font-label-lg text-label-lg text-xs uppercase tracking-wider text-center">Timer</th>
              <th className="px-6 py-4 font-label-lg text-label-lg text-xs uppercase tracking-wider text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/30">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
              : users.map(user => (
                  <UserRow
                    key={user.id}
                    user={user}
                    isSelf={user.id === currentUserId}
                    onRequestRoleChange={onRequestRoleChange}
                  />
                ))
            }
          </tbody>
        </table>
      </div>

      {/* Empty state */}
      {!loading && users.length === 0 && (
        <div className="py-16 flex flex-col items-center gap-3 text-on-surface-variant">
          <span className="material-symbols-outlined text-4xl opacity-30">group_off</span>
          <p className="text-sm">No se encontraron usuarios con ese criterio.</p>
        </div>
      )}
    </div>
  );
}

// ── Fila individual ───────────────────────────────────────────────────────────

function UserRow({ user, isSelf, onRequestRoleChange }) {
  const displayName = user.full_name || user.username || '—';
  const rowBg = isSelf
    ? 'bg-primary/5 hover:bg-primary/10'
    : 'hover:bg-surface-variant/20';

  return (
    <tr className={`${rowBg} transition-colors`}>

      {/* Usuario */}
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <Avatar name={displayName} src={user.avatar_url} isSelf={isSelf} />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-bold text-on-surface text-sm">{displayName}</span>
              {isSelf && (
                <span className="bg-secondary/20 text-secondary text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-tighter flex-shrink-0">
                  Tú
                </span>
              )}
            </div>
            <code className="text-on-surface-variant text-xs font-mono">@{user.username}</code>
          </div>
        </div>
      </td>

      {/* Email */}
      <td className="px-6 py-4 text-on-surface-variant text-sm">
        <span className="truncate block max-w-[160px]" title={user.email}>{user.email}</span>
      </td>

      {/* Rol */}
      <td className="px-6 py-4">
        <RoleSelect
          userId={user.id}
          currentRole={user.role}
          currentUserId={isSelf ? user.id : null}
          onRequest={(uid, newRole) => onRequestRoleChange(uid, newRole, displayName)}
        />
      </td>

      {/* Estado email — backend retorna email_verified (bool) */}
      <td className="px-6 py-4">
        <EmailStatus status={user.email_verified ? 'verified' : 'pending'} />
      </td>

      {/* Fecha registro */}
      <td className="px-6 py-4 text-on-surface-variant text-sm whitespace-nowrap">
        {formatRelativeTime(user.created_at)}
      </td>

      {/* Timer activo */}
      <td className="px-6 py-4 text-center">
        <TimerStatus hasTimer={user.has_active_timer} taskName={user.active_timer_task} />
      </td>

      {/* Acciones contextual */}
      <td className="px-6 py-4 text-right">
        <ActionsMenu user={user} isSelf={isSelf} displayName={displayName} />
      </td>
    </tr>
  );
}

// ── Menú contextual ───────────────────────────────────────────────────────────

function ActionsMenu({ user, isSelf, displayName }) {
  const [open, setOpen] = React.useState(false);
  const menuRef = React.useRef(null);

  React.useEffect(() => {
    const handler = (e) => { if (!menuRef.current?.contains(e.target)) setOpen(false); };
    if (open) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div className="relative inline-block" ref={menuRef}>
      <button
        onClick={() => setOpen(v => !v)}
        className="p-1.5 hover:bg-surface-variant rounded-full transition-colors text-on-surface-variant hover:text-on-surface"
        aria-label={`Acciones para ${displayName}`}
        aria-expanded={open}
      >
        <span className="material-symbols-outlined">more_vert</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-44 bg-surface-container-highest border border-outline-variant rounded-xl shadow-xl z-30 py-1">
          <MenuItem icon="visibility" label="Ver perfil" onClick={() => setOpen(false)} />
          {!isSelf && (
            <>
              <MenuItem icon="send" label="Enviar mensaje" onClick={() => setOpen(false)} />
              <div className="my-1 border-t border-outline-variant/40" />
              <MenuItem icon="block" label="Desactivar cuenta" danger onClick={() => setOpen(false)} />
            </>
          )}
        </div>
      )}
    </div>
  );
}

function MenuItem({ icon, label, danger = false, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2 px-4 py-2 text-sm transition-colors
        ${danger
          ? 'text-error hover:bg-error/10'
          : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/60'
        }`}
    >
      <span className="material-symbols-outlined text-[16px]">{icon}</span>
      {label}
    </button>
  );
}