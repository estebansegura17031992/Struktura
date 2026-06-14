/**
 * useMembers.js
 * Hook — Panel de Miembros del Proyecto
 * Sprint 2 · E03 · R-0304 · R-0305
 *
 * Maneja:
 *   - Fetch miembros activos y historial colapsable
 *   - Modal remover miembro (con detección de timer activo)
 *   - Modal transferir ownership (búsqueda + confirmación por username)
 */
import { useState, useEffect, useCallback } from "react";
import api from "../api/axiosInstance";

// ── API calls ──────────────────────────────────────────────────────────────────

async function fetchActiveMembers(projectId) {
  const { data } = await api.get(`/projects/${projectId}/members`);
  return data;
}

async function fetchMemberHistory(projectId, page = 1) {
  const { data } = await api.get(
    `/projects/${projectId}/members/history?page=${page}&page_size=20`
  );
  return data;
}

async function apiRemoveMember(projectId, userId) {
  await api.delete(`/projects/${projectId}/members/${userId}`);
}

async function apiTransferOwnership(projectId, newOwnerId) {
  const { data } = await api.post(`/projects/${projectId}/transfer-ownership`, {
    new_owner_id: newOwnerId,
  });
  return data;
}

// ── Hook principal ─────────────────────────────────────────────────────────────

export function useMembers(projectId) {
  // ── Miembros activos ────────────────────────────────────────────────────────
  const [members, setMembers]       = useState([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);

  // ── Historial ───────────────────────────────────────────────────────────────
  const [historyOpen, setHistoryOpen]   = useState(false);
  const [history, setHistory]           = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyTotal, setHistoryTotal] = useState(0);

  // ── Modal remover ───────────────────────────────────────────────────────────
  const [removingMember, setRemovingMember] = useState(null);
  const [removing, setRemoving]             = useState(false);
  const [removeError, setRemoveError]       = useState(null);

  // ── Modal transferir ownership ──────────────────────────────────────────────
  const [showTransfer, setShowTransfer]     = useState(false);
  const [transferring, setTransferring]     = useState(false);
  const [transferError, setTransferError]   = useState(null);

  // ── Carga miembros activos ──────────────────────────────────────────────────

  const loadMembers = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchActiveMembers(projectId);
      setMembers(Array.isArray(data) ? data : data.items ?? []);
    } catch (e) {
      const status = e?.response?.status;
      setError(
        status === 403
          ? "No tienes permisos para ver los miembros de este proyecto."
          : "Error al cargar miembros. Intenta de nuevo."
      );
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { loadMembers(); }, [loadMembers]);

  // ── Historial colapsable ────────────────────────────────────────────────────

  const toggleHistory = useCallback(async () => {
    if (!historyOpen && history.length === 0) {
      setHistoryLoading(true);
      try {
        const data = await fetchMemberHistory(projectId);
        // Filtrar solo los removidos (is_active = false)
        const removed = (data.items ?? []).filter(m => !m.is_active);
        setHistory(removed);
        setHistoryTotal(data.total ?? removed.length);
      } catch {
        // Silencioso — el historial es opcional
      } finally {
        setHistoryLoading(false);
      }
    }
    setHistoryOpen(v => !v);
  }, [historyOpen, history.length, projectId]);

  // ── Remover miembro ─────────────────────────────────────────────────────────

  const openRemove  = useCallback((member) => {
    setRemoveError(null);
    setRemovingMember(member);
  }, []);

  const closeRemove = useCallback(() => {
    setRemovingMember(null);
    setRemoveError(null);
  }, []);

  const confirmRemove = useCallback(async () => {
    if (!removingMember) return;
    setRemoving(true);
    setRemoveError(null);
    try {
      await apiRemoveMember(projectId, removingMember.user_id);
      setMembers(prev => prev.filter(m => m.user_id !== removingMember.user_id));
      // Invalidar historial para que recargue
      setHistory([]);
      setRemovingMember(null);
    } catch (e) {
      const code = e?.response?.data?.error?.code;
      if (code === "CANNOT_REMOVE_OWNER") {
        setRemoveError("No puedes remover al owner. Transfiere el ownership primero.");
      } else if (e?.response?.status === 403) {
        setRemoveError("No tienes permisos para remover miembros.");
      } else {
        setRemoveError("Error al remover el miembro. Intenta de nuevo.");
      }
    } finally {
      setRemoving(false);
    }
  }, [removingMember, projectId]);

  // ── Transferir ownership ────────────────────────────────────────────────────

  const openTransfer  = useCallback(() => {
    setTransferError(null);
    setShowTransfer(true);
  }, []);

  const closeTransfer = useCallback(() => {
    setShowTransfer(false);
    setTransferError(null);
  }, []);

  const confirmTransfer = useCallback(async (newOwnerId) => {
    setTransferring(true);
    setTransferError(null);
    try {
      await apiTransferOwnership(projectId, newOwnerId);
      // Recargar miembros para reflejar nuevos roles
      await loadMembers();
      setShowTransfer(false);
    } catch (e) {
      const code = e?.response?.data?.error?.code;
      const msg  = e?.response?.data?.error?.message;
      if (code === "NOT_FOUND") {
        setTransferError("El nuevo owner debe ser miembro activo del proyecto.");
      } else if (code === "INVALID_OPERATION") {
        setTransferError("No puedes transferirte el ownership a ti mismo.");
      } else {
        setTransferError(msg ?? "Error al transferir el ownership. Intenta de nuevo.");
      }
    } finally {
      setTransferring(false);
    }
  }, [projectId, loadMembers]);

  return {
    // Miembros
    members, loading, error, refresh: loadMembers,
    // Historial
    historyOpen, toggleHistory,
    history, historyLoading, historyTotal,
    // Remover
    removingMember, openRemove, closeRemove,
    removing, removeError, confirmRemove,
    // Transferir
    showTransfer, openTransfer, closeTransfer,
    transferring, transferError, confirmTransfer,
  };
}