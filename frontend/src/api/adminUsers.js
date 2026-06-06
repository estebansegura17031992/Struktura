/**
 * AdminUsersPage.jsx
 * Página: Panel Administración de Usuarios
 * Sprint 2 · E02 · R-0204 · R-0205 · R-0206
 *
 * Props:
 *   currentUserId {string} — ID del usuario autenticado (desde Zustand store)
 *
 * Conecta a:
 *   GET  /admin/users                     — listado paginado con filtros
 *   PATCH /admin/users/{id}/role          — cambio de rol con confirmación
 *
 * Guard: esta ruta debe estar protegida con require_role('admin')
 * en el router (PrivateRoute) antes de renderizar este componente.
 */

import React from 'react';
import { useAdminUsers } from '../hooks/useAdminUsers';
import { UsersTable } from '../components/UsersTable';
import { ConfirmRoleModal } from '../components/ConfirmRoleModal';
import { Pagination, Spinner } from '../components/DesignSystem';

export default function AdminUsersPage({ currentUserId }) {
  const {
    users, total, page, pageSize, totalPages,
    loading, error,
    search, setSearch,
    roleFilter, setRoleFilter,
    setPage,
    pendingRoleChange, requestRoleChange, confirmRoleChange, cancelRoleChange,
    roleChangeLoading, roleChangeError,
    refresh,
  } = useAdminUsers(currentUserId);

  return (
    <div className="p-6 flex-1 overflow-x-hidden">

      {/* ── Toolbar ──────────────────────────────────────────────── */}
      <section className="mb-6 flex flex-wrap items-center justify-between gap-6">

        {/* Búsqueda + filtro rol */}
        <div className="flex items-center gap-3 flex-1 min-w-[280px]">
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
              aria-label="Buscar usuarios"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
                aria-label="Limpiar búsqueda"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            )}
          </div>

          <div className="relative">
            <select
              value={roleFilter}
              onChange={e => setRoleFilter(e.target.value)}
              className="appearance-none bg-surface-container-low border border-outline-variant rounded-full py-2.5 pl-4 pr-10 text-sm focus:outline-none focus:border-secondary cursor-pointer"
              aria-label="Filtrar por rol"
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

        {/* Contador + CTA */}
        <div className="flex items-center gap-4">
          {loading ? (
            <Spinner size={16} />
          ) : (
            <span className="text-on-surface-variant text-sm">
              <strong className="text-on-surface">{total}</strong> usuarios
            </span>
          )}
          <button
            className="bg-primary-container text-on-primary-container hover:opacity-90 transition-opacity px-6 py-2.5 rounded-full font-label-lg text-label-lg flex items-center gap-2 text-sm"
            aria-label="Invitar nuevo usuario"
          >
            <span className="material-symbols-outlined text-[18px]">person_add</span>
            Nuevo Usuario
          </button>
        </div>
      </section>

      {/* ── Error state ───────────────────────────────────────────── */}
      {error && (
        <div className="mb-6 px-5 py-4 bg-error-container/20 border border-error/30 rounded-xl text-error flex items-center gap-3">
          <span className="material-symbols-outlined flex-shrink-0">error</span>
          <span className="text-sm flex-1">{error}</span>
          <button
            onClick={refresh}
            className="text-sm font-bold underline underline-offset-2 hover:no-underline"
          >
            Reintentar
          </button>
        </div>
      )}

      {/* ── Tabla ────────────────────────────────────────────────── */}
      <UsersTable
        users={users}
        loading={loading}
        currentUserId={currentUserId}
        onRequestRoleChange={requestRoleChange}
      />

      {/* ── Paginación ───────────────────────────────────────────── */}
      {!loading && total > pageSize && (
        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          pageSize={pageSize}
          onPageChange={setPage}
        />
      )}

      {/* ── Modal confirmación cambio de rol ─────────────────────── */}
      <ConfirmRoleModal
        pending={pendingRoleChange}
        loading={roleChangeLoading}
        error={roleChangeError}
        onConfirm={confirmRoleChange}
        onCancel={cancelRoleChange}
      />
    </div>
  );
}