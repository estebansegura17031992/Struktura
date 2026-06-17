/**
 * DesignSystem.jsx
 * Componentes atómicos — Design System Struktura
 * Colores, badges, avatares, chips de rol, spinner, paginación
 */

import React from 'react';

// ── Constantes de rol ────────────────────────────────────────────────────────

export const ROLE_META = {
  admin:  { label: 'Admin',  color: 'text-amber-400',   bg: 'bg-amber-400/10',  border: 'border-amber-400/20'  },
  editor: { label: 'Editor', color: 'text-violet-400',  bg: 'bg-violet-400/10', border: 'border-violet-400/20' },
  viewer: { label: 'Viewer', color: 'text-on-surface-variant', bg: 'bg-surface-variant', border: 'border-outline-variant' },
};

// ── RoleBadge ─────────────────────────────────────────────────────────────────

export function RoleBadge({ role, className = '' }) {
  const m = ROLE_META[role] ?? ROLE_META.viewer;
  return (
    <span className={`inline-flex items-center text-xs font-bold px-3 py-1 rounded-full border ${m.bg} ${m.color} ${m.border} ${className}`}>
      {m.label}
    </span>
  );
}

// ── RoleSelect ────────────────────────────────────────────────────────────────
// Dropdown inline para cambio de rol — deshabilitado para el usuario actual

export function RoleSelect({ userId, currentRole, currentUserId, onRequest, disabled = false }) {
  const isSelf = userId === currentUserId;
  const m = ROLE_META[currentRole] ?? ROLE_META.viewer;

  if (isSelf) {
    return (
      <div className="relative group inline-block">
        <span className={`inline-flex items-center text-xs font-bold px-3 py-1 rounded-full border cursor-help ${m.bg} ${m.color} ${m.border}`}>
          {m.label}
        </span>
        <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all bg-surface-container-highest text-on-surface text-[10px] py-1 px-3 rounded-lg shadow-lg z-20 whitespace-nowrap">
          No puedes cambiar tu propio rol
        </div>
      </div>
    );
  }

  return (
    <div className="relative group inline-flex items-center bg-surface-variant/40 rounded-full px-2 py-1 gap-1 border border-outline-variant hover:border-secondary/50 transition-colors">
      <select
        value={currentRole}
        disabled={disabled}
        onChange={e => onRequest(userId, e.target.value)}
        className="bg-transparent border-none text-xs font-bold text-on-surface focus:ring-0 cursor-pointer p-0 appearance-none disabled:opacity-50"
        aria-label="Cambiar rol"
      >
        <option value="admin">Admin</option>
        <option value="editor">Editor</option>
        <option value="viewer">Viewer</option>
      </select>
      <span className="material-symbols-outlined text-[14px] text-on-surface-variant pointer-events-none">expand_more</span>
    </div>
  );
}

// ── Avatar ────────────────────────────────────────────────────────────────────

export function Avatar({ name, src, isSelf = false, size = 'md' }) {
  const sz = size === 'sm' ? 'w-8 h-8 text-xs' : 'w-10 h-10 text-sm';
  const initials = (name ?? '?').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  const colors = ['bg-primary/20 text-primary', 'bg-secondary/20 text-secondary', 'bg-violet-500/20 text-violet-400'];
  const colorIdx = (name?.charCodeAt(0) ?? 0) % colors.length;

  return (
    <div className={`relative flex-shrink-0 ${sz} rounded-full overflow-hidden ${isSelf ? 'ring-2 ring-primary' : ''}`}>
      {src ? (
        <img src={src} alt={name} className="w-full h-full object-cover" />
      ) : (
        <div className={`w-full h-full flex items-center justify-center font-bold ${colors[colorIdx]}`}>
          {initials}
        </div>
      )}
    </div>
  );
}

// ── EmailStatus ───────────────────────────────────────────────────────────────

export function EmailStatus({ status }) {
  if (status === 'verified') {
    return (
      <span className="flex items-center gap-1.5 text-secondary text-sm">
        <span className="material-symbols-outlined text-[16px]" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
        Verificado
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1.5 text-on-surface-variant text-sm italic">
      <span className="material-symbols-outlined text-[16px]">pending_actions</span>
      Pendiente
    </span>
  );
}

// ── TimerStatus ───────────────────────────────────────────────────────────────

export function TimerStatus({ hasTimer, taskName }) {
  if (!hasTimer) {
    return <span className="material-symbols-outlined text-on-surface-variant opacity-20">timer_off</span>;
  }
  return (
    <div className="relative group inline-block">
      <span className="w-3 h-3 bg-secondary rounded-full inline-block pulse-dot" />
      {taskName && (
        <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all bg-surface-container-highest text-on-surface text-[10px] py-1 px-3 rounded-lg shadow-lg z-10 whitespace-nowrap">
          Timer activo en <strong>{taskName}</strong>
        </div>
      )}
    </div>
  );
}

// ── Spinner ───────────────────────────────────────────────────────────────────

export function Spinner({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="animate-spin">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeOpacity="0.2" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

// ── SkeletonRow ───────────────────────────────────────────────────────────────

export function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      {[160, 130, 70, 90, 80, 40, 30].map((w, i) => (
        <td key={i} className="px-6 py-4">
          <div className="h-4 bg-surface-variant/50 rounded-full" style={{ width: w }} />
        </td>
      ))}
    </tr>
  );
}

// ── Pagination ────────────────────────────────────────────────────────────────

export function Pagination({ page, totalPages, total, pageSize, onPageChange }) {
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to   = Math.min(page * pageSize, total);

  const pages = buildPageRange(page, totalPages);

  return (
    <footer className="mt-6 flex items-center justify-between flex-wrap gap-4">
      <p className="text-on-surface-variant text-sm">
        Mostrando <span className="text-on-surface font-medium">{from}–{to}</span> de{' '}
        <span className="text-on-surface font-medium">{total}</span> usuarios
      </p>
      <div className="flex items-center gap-2">
        <PageBtn onClick={() => onPageChange(page - 1)} disabled={page === 1} icon="chevron_left" />
        {pages.map((p, i) =>
          p === '…' ? (
            <span key={`e${i}`} className="w-10 text-center text-on-surface-variant text-sm">…</span>
          ) : (
            <PageBtn key={p} label={p} active={p === page} onClick={() => onPageChange(p)} />
          )
        )}
        <PageBtn onClick={() => onPageChange(page + 1)} disabled={page === totalPages} icon="chevron_right" />
      </div>
    </footer>
  );
}

function PageBtn({ label, active, onClick, disabled, icon }) {
  const base = 'w-10 h-10 flex items-center justify-center rounded-lg font-bold text-sm transition-colors';
  const style = active
    ? `${base} bg-primary-container text-on-primary-container`
    : disabled
    ? `${base} border border-outline-variant text-on-surface-variant opacity-30 cursor-not-allowed`
    : `${base} border border-outline-variant text-on-surface-variant hover:bg-surface-variant`;

  return (
    <button className={style} onClick={onClick} disabled={disabled || active}>
      {icon ? <span className="material-symbols-outlined">{icon}</span> : label}
    </button>
  );
}

function buildPageRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, '…', total];
  if (current >= total - 3) return [1, '…', total-4, total-3, total-2, total-1, total];
  return [1, '…', current-1, current, current+1, '…', total];
}