/**
 * useAdminUsers.js
 * Hook personalizado — Panel Administración de Usuarios
 * Maneja: fetch paginado, búsqueda debounced, filtro de rol, cambio de rol + confirmación
 * Sprint 2 · E02 · R-0204
 *
 * Compatibilidad con el proyecto:
 *   - Errores via axios: e.response.status / e.response.data.error.code
 *   - Token gestionado por axiosInstance.js (interceptor automático)
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { fetchUsers, updateUserRole } from "../api/adminUsers";

const PAGE_SIZE = 20;

/**
 * @returns {{
 *   users: import('../api/adminUsers').User[],
 *   total: number,
 *   page: number,
 *   pageSize: number,
 *   totalPages: number,
 *   loading: boolean,
 *   error: string|null,
 *   search: string,
 *   setSearch: Function,
 *   roleFilter: string,
 *   setRoleFilter: Function,
 *   setPage: Function,
 *   pendingRoleChange: {userId:string, newRole:string, userName:string}|null,
 *   requestRoleChange: Function,
 *   confirmRoleChange: Function,
 *   cancelRoleChange: Function,
 *   roleChangeLoading: boolean,
 *   roleChangeError: string|null,
 *   refresh: Function,
 * }}
 */
export function useAdminUsers() {
  const [users, setUsers]               = useState([]);
  const [total, setTotal]               = useState(0);
  const [page, setPage]                 = useState(1);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);
  const [search, setSearchRaw]          = useState("");
  const [debouncedSearch, setDebounced] = useState("");
  const [roleFilter, setRoleFilter]     = useState("");

  const [pendingRoleChange, setPending]   = useState(null);
  const [roleChangeLoading, setRcLoading] = useState(false);
  const [roleChangeError, setRcError]     = useState(null);

  const debounceRef = useRef(null);

  // Búsqueda con debounce 350ms
  const setSearch = useCallback((val) => {
    setSearchRaw(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebounced(val);
      setPage(1);
    }, 350);
  }, []);

  const handleSetRoleFilter = useCallback((val) => {
    setRoleFilter(val);
    setPage(1);
  }, []);

  // Carga de datos
  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchUsers({
        page,
        page_size: PAGE_SIZE,
        search: debouncedSearch,
        role: roleFilter,
      });
      setUsers(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      const status = e?.response?.status;
      if (status === 403) {
        setError("No tienes permisos para acceder a esta sección.");
      } else if (status === 401) {
        setError("Sesión expirada. Por favor inicia sesión nuevamente.");
      } else {
        setError("Error al cargar usuarios. Intenta de nuevo.");
      }
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch, roleFilter]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // Solicitar cambio de rol — abre modal de confirmación
  const requestRoleChange = useCallback((userId, newRole, userName) => {
    setRcError(null);
    setPending({ userId, newRole, userName });
  }, []);

  // Confirmar y ejecutar cambio
  const confirmRoleChange = useCallback(async () => {
    if (!pendingRoleChange) return;
    setRcLoading(true);
    setRcError(null);
    try {
      const updated = await updateUserRole(
        pendingRoleChange.userId,
        pendingRoleChange.newRole
      );
      // Actualizar optimísticamente en lista local
      setUsers((prev) =>
        prev.map((u) => (u.id === updated.id ? { ...u, role: updated.role } : u))
      );
      setPending(null);
    } catch (e) {
      const status = e?.response?.status;
      const code   = e?.response?.data?.error?.code;

      if (status === 422 && code === "CANNOT_REMOVE_LAST_ADMIN") {
        setRcError("No puedes degradar al único administrador del sistema.");
      } else if (status === 403) {
        setRcError("No tienes permisos para cambiar este rol.");
      } else if (status === 404) {
        setRcError("Usuario no encontrado.");
      } else {
        setRcError("Error al cambiar el rol. Intenta de nuevo.");
      }
    } finally {
      setRcLoading(false);
    }
  }, [pendingRoleChange]);

  const cancelRoleChange = useCallback(() => {
    setPending(null);
    setRcError(null);
  }, []);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return {
    users,
    total,
    page,
    pageSize: PAGE_SIZE,
    totalPages,
    loading,
    error,
    search,
    setSearch,
    roleFilter,
    setRoleFilter: handleSetRoleFilter,
    setPage,
    pendingRoleChange,
    requestRoleChange,
    confirmRoleChange,
    cancelRoleChange,
    roleChangeLoading,
    roleChangeError,
    refresh: loadUsers,
  };
}