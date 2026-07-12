/**
 * useTasks.js
 * Hook principal — Tablero Kanban de un proyecto
 * Sprint 3 · E04 · R-0401 a R-0405
 *
 * GET /tasks se llama una sola vez sin filtro de status (el backend regresa
 * las 3 columnas juntas); este hook las separa client-side. Filtros de
 * prioridad/asignado/búsqueda se re-consultan al backend (FTS vive ahí).
 */
import { useState, useEffect, useCallback, useRef } from "react";
import {
  fetchTasks, createTask, updateTask, updateTaskStatus,
  updateTaskAssignees, deleteTask,
} from "../api/tasks";

const STATUSES = ["abierto", "en_proceso", "completo"];
const PAGE_SIZE = 50;

export function useTasks(projectId) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [priority, setPriority] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const [search, setSearchRaw] = useState("");
  const [debouncedSearch, setDebounced] = useState("");

  const debounceRef = useRef(null);

  const setSearch = useCallback((val) => {
    setSearchRaw(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebounced(val), 300);
  }, []);

  const load = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTasks({
        project_id: projectId,
        priority: priority || undefined,
        assigned_to: assignedTo || undefined,
        search: debouncedSearch.trim().length >= 2 ? debouncedSearch : undefined,
        page_size: PAGE_SIZE,
      });
      setTasks(data.items ?? []);
    } catch (e) {
      const status = e?.response?.status;
      setError(
        status === 403
          ? "No tienes permisos para ver las tareas de este proyecto."
          : "Error al cargar el tablero. Intenta de nuevo."
      );
    } finally {
      setLoading(false);
    }
  }, [projectId, priority, assignedTo, debouncedSearch]);

  useEffect(() => { load(); }, [load]);

  const hasActiveFilters = Boolean(priority || assignedTo || debouncedSearch.trim().length >= 2);

  const clearFilters = useCallback(() => {
    setPriority("");
    setAssignedTo("");
    setSearchRaw("");
    setDebounced("");
  }, []);

  const columns = STATUSES.reduce((acc, status) => {
    acc[status] = tasks.filter((t) => t.status === status);
    return acc;
  }, {});

  // ── Modal crear ──────────────────────────────────────────────────────────
  const [showCreate, setShowCreate]   = useState(false);
  const [creating, setCreating]       = useState(false);
  const [createError, setCreateError] = useState(null);

  const openCreateTask  = useCallback(() => { setCreateError(null); setShowCreate(true); }, []);
  const closeCreateTask = useCallback(() => { setShowCreate(false); setCreateError(null); }, []);

  const submitCreateTask = useCallback(async ({ title, description, priority: p, due_date, assignee_ids }) => {
    if (!projectId) return;
    setCreating(true);
    setCreateError(null);
    try {
      const created = await createTask({
        title,
        description: description || null,
        priority: p,
        due_date: due_date || null,
        project_id: projectId,
        assignee_ids: assignee_ids ?? [],
      });
      setTasks((prev) => [created, ...prev]);
      setShowCreate(false);
    } catch (e) {
      const code = e?.response?.data?.error?.code;
      const msg  = e?.response?.data?.error?.message;
      setCreateError(
        code === "MAX_ASSIGNEES_EXCEEDED"
          ? (msg ?? "Se excedió el máximo de asignados permitido.")
          : "Error al crear la tarea. Intenta de nuevo."
      );
    } finally {
      setCreating(false);
    }
  }, [projectId]);

  // ── Modal editar ─────────────────────────────────────────────────────────
  const [editingTask, setEditingTask] = useState(null);
  const [updating, setUpdating]       = useState(false);
  const [editError, setEditError]     = useState(null);

  const openEditTask  = useCallback((task) => { setEditError(null); setEditingTask(task); }, []);
  const closeEditTask = useCallback(() => { setEditingTask(null); setEditError(null); }, []);

  const submitEditTask = useCallback(async ({ title, description, priority: p, due_date, assignee_ids, status }) => {
    if (!editingTask) return;
    setUpdating(true);
    setEditError(null);
    try {
      let updated = await updateTask(editingTask.id, {
        title,
        description: description || null,
        priority: p,
        due_date: due_date || null,
      });

      // Los asignados usan el endpoint dedicado — ahí vive la lógica ADR-03
      // (detener el timer al pasar de 1 a 2+ asignados). No pasar assignee_ids
      // por el PATCH genérico o se saltaría esa regla.
      const currentIds = (editingTask.assignees ?? []).map((a) => a.id).sort().join(",");
      const nextIds = [...(assignee_ids ?? [])].sort().join(",");
      if (nextIds !== currentIds) {
        updated = await updateTaskAssignees(editingTask.id, assignee_ids ?? []);
      }

      // El status vive en su propio endpoint (RBAC especial: editor/admin o
      // asignado; viewer nunca puede).
      if (status && status !== editingTask.status) {
        updated = await updateTaskStatus(editingTask.id, status);
      }

      setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      setEditingTask(null);
    } catch (e) {
      const code = e?.response?.data?.error?.code;
      const msg  = e?.response?.data?.error?.message;
      if (e?.response?.status === 403) {
        setEditError("No tienes permisos para editar esta tarea.");
      } else if (code === "MAX_ASSIGNEES_EXCEEDED") {
        setEditError(msg ?? "Se excedió el máximo de asignados permitido.");
      } else {
        setEditError("Error al actualizar la tarea. Intenta de nuevo.");
      }
    } finally {
      setUpdating(false);
    }
  }, [editingTask]);

  const [deleting, setDeleting]     = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const submitDeleteTask = useCallback(async () => {
    if (!editingTask) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteTask(editingTask.id);
      setTasks((prev) => prev.filter((t) => t.id !== editingTask.id));
      setEditingTask(null);
    } catch (e) {
      setDeleteError(
        e?.response?.status === 403
          ? "No tienes permisos para eliminar esta tarea."
          : "Error al eliminar la tarea. Intenta de nuevo."
      );
    } finally {
      setDeleting(false);
    }
  }, [editingTask]);

  return {
    columns,
    total: tasks.length,
    loading,
    error,
    refresh: load,
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
  };
}
