/**
 * useProjects.js
 * Hook principal — Pantalla listado de proyectos
 * Sprint 2 · E03 · R-0301 a R-0303
 *
 * Maneja:
 *   - Fetch paginado con búsqueda debounced
 *   - Toggle vista grid/list
 *   - Modal crear proyecto
 *   - Modal editar proyecto
 *   - Modal confirmar eliminación (con manejo PROJECT_HAS_ACTIVE_TASKS)
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { fetchProjects, createProject, updateProject, deleteProject } from "../api/projects";

const PAGE_SIZE = 20;

export function useProjects() {
  // ── Listado ──────────────────────────────────────────────────────────────
  const [projects, setProjects]     = useState([]);
  const [total, setTotal]           = useState(0);
  const [page, setPage]             = useState(1);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);
  const [search, setSearchRaw]      = useState("");
  const [debouncedSearch, setDebounced] = useState("");
  const [viewMode, setViewMode]     = useState("grid"); // "grid" | "list"

  const debounceRef = useRef(null);

  const setSearch = useCallback((val) => {
    setSearchRaw(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebounced(val);
      setPage(1);
    }, 350);
  }, []);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProjects({ page, page_size: PAGE_SIZE, search: debouncedSearch });
      setProjects(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      const status = e?.response?.status;
      setError(
        status === 403
          ? "No tienes permisos para ver esta sección."
          : "Error al cargar proyectos. Intenta de nuevo."
      );
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch]);

  useEffect(() => { loadProjects(); }, [loadProjects]);

  // ── Modal crear ──────────────────────────────────────────────────────────
  const [showCreate, setShowCreate]   = useState(false);
  const [creating, setCreating]       = useState(false);
  const [createError, setCreateError] = useState(null);

  const openCreate  = useCallback(() => { setCreateError(null); setShowCreate(true); }, []);
  const closeCreate = useCallback(() => { setShowCreate(false); setCreateError(null); }, []);

  const submitCreate = useCallback(async ({ name, description }) => {
    setCreating(true);
    setCreateError(null);
    try {
      const newProject = await createProject({ name, description });
      setProjects(prev => [newProject, ...prev]);
      setTotal(prev => prev + 1);
      setShowCreate(false);
    } catch (e) {
      const code = e?.response?.data?.error?.code;
      const msg  = e?.response?.data?.error?.message;
      if (code === "PROJECT_LIMIT_REACHED") {
        setCreateError(msg ?? "Has alcanzado el límite de proyectos.");
      } else {
        setCreateError("Error al crear el proyecto. Intenta de nuevo.");
      }
    } finally {
      setCreating(false);
    }
  }, []);

  // ── Modal editar ─────────────────────────────────────────────────────────
  const [editingProject, setEditingProject] = useState(null);
  const [updating, setUpdating]             = useState(false);
  const [editError, setEditError]           = useState(null);

  const openEdit  = useCallback((project) => { setEditError(null); setEditingProject(project); }, []);
  const closeEdit = useCallback(() => { setEditingProject(null); setEditError(null); }, []);

  const submitEdit = useCallback(async ({ name, description }) => {
    if (!editingProject) return;
    setUpdating(true);
    setEditError(null);
    try {
      const updated = await updateProject(editingProject.id, { name, description });
      setProjects(prev => prev.map(p => p.id === updated.id ? { ...p, ...updated } : p));
      setEditingProject(null);
    } catch (e) {
      setEditError("Error al actualizar el proyecto. Intenta de nuevo.");
    } finally {
      setUpdating(false);
    }
  }, [editingProject]);

  // ── Modal eliminar ───────────────────────────────────────────────────────
  const [deletingProject, setDeletingProject] = useState(null);
  const [deleting, setDeleting]               = useState(false);
  const [deleteError, setDeleteError]         = useState(null);
  const [blockingTasks, setBlockingTasks]     = useState([]);

  const openDelete  = useCallback((project) => {
    setDeleteError(null);
    setBlockingTasks([]);
    setDeletingProject(project);
  }, []);
  const closeDelete = useCallback(() => {
    setDeletingProject(null);
    setDeleteError(null);
    setBlockingTasks([]);
  }, []);

  const submitDelete = useCallback(async () => {
    if (!deletingProject) return;
    setDeleting(true);
    setDeleteError(null);
    setBlockingTasks([]);
    try {
      await deleteProject(deletingProject.id);
      setProjects(prev => prev.filter(p => p.id !== deletingProject.id));
      setTotal(prev => prev - 1);
      setDeletingProject(null);
    } catch (e) {
      const code = e?.response?.data?.error?.code;
      const msg  = e?.response?.data?.error?.message;
      if (code === "PROJECT_HAS_ACTIVE_TASKS") {
        setDeleteError(msg ?? "El proyecto tiene tareas activas.");
        // El backend puede enviar lista de tareas bloqueantes en details
        setBlockingTasks(e?.response?.data?.error?.details?.blocking_tasks ?? []);
      } else {
        setDeleteError("Error al eliminar el proyecto. Intenta de nuevo.");
      }
    } finally {
      setDeleting(false);
    }
  }, [deletingProject]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return {
    // Listado
    projects, total, page, pageSize: PAGE_SIZE, totalPages,
    loading, error, search, setSearch, setPage,
    viewMode, setViewMode,
    refresh: loadProjects,
    // Crear
    showCreate, openCreate, closeCreate,
    creating, createError, submitCreate,
    // Editar
    editingProject, openEdit, closeEdit,
    updating, editError, submitEdit,
    // Eliminar
    deletingProject, openDelete, closeDelete,
    deleting, deleteError, blockingTasks, submitDelete,
  };
}