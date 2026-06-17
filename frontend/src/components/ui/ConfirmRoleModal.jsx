/**
 * ConfirmRoleModal.jsx
 * Modal de confirmación para cambio de rol
 * Cubre: caso happy path, caso "último admin" (R-0201 regla de negocio)
 */

import React, { useEffect, useRef } from 'react';
import { ROLE_META, Spinner } from './DesignSystem';

const ROLE_COLOR = {
  admin:  'text-amber-400',
  editor: 'text-violet-400',
  viewer: 'text-on-surface-variant',
};

export function ConfirmRoleModal({ pending, loading, error, onConfirm, onCancel }) {
  const confirmRef = useRef(null);

  // Foco en botón confirmar al abrir
  useEffect(() => {
    if (pending) confirmRef.current?.focus();
  }, [pending]);

  // Cerrar con Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onCancel(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onCancel]);

  if (!pending) return null;

  const roleMeta = ROLE_META[pending.newRole] ?? ROLE_META.viewer;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div className="bg-surface-container-high border border-outline-variant rounded-2xl shadow-2xl w-full max-w-sm p-6 animate-in fade-in zoom-in-95 duration-200">

          {/* Ícono */}
          <div className="w-12 h-12 rounded-full bg-primary-container/30 flex items-center justify-center mb-4 mx-auto">
            <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>
              manage_accounts
            </span>
          </div>

          <h2 id="modal-title" className="text-on-surface font-bold text-base text-center mb-2">
            Cambiar rol de usuario
          </h2>

          <p className="text-on-surface-variant text-sm text-center leading-relaxed mb-5">
            ¿Confirmas que deseas otorgar permisos de{' '}
            <span className={`font-bold ${ROLE_COLOR[pending.newRole] ?? ''}`}>
              {roleMeta.label.toLowerCase()}
            </span>{' '}
            a <span className="text-on-surface font-medium">{pending.userName}</span>?
          </p>

          {/* Error */}
          {error && (
            <div className="mb-4 px-4 py-3 bg-error-container/30 border border-error/30 rounded-xl text-error text-xs flex items-start gap-2">
              <span className="material-symbols-outlined text-[16px] flex-shrink-0 mt-0.5">error</span>
              <span>{error}</span>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={onCancel}
              disabled={loading}
              className="flex-1 bg-surface-variant text-on-surface text-sm font-bold py-2.5 rounded-xl hover:bg-surface-bright transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              ref={confirmRef}
              onClick={onConfirm}
              disabled={loading}
              className="flex-1 bg-primary-container text-on-primary-container text-sm font-bold py-2.5 rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? <Spinner size={16} /> : null}
              {loading ? 'Guardando…' : 'Sí, confirmar'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}