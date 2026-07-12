/**
 * tasks.js
 * Capa de acceso a API — Tareas y tablero Kanban
 * Sprint 3 · E04 · R-0401 a R-0405
 *
 * Usa la instancia axios del proyecto (axiosInstance.js):
 *   - Token inyectado automáticamente por interceptor
 *   - Silent refresh en 401
 */
import api from "./axiosInstance";

// ── Tareas ─────────────────────────────────────────────────────────────────────

/**
 * GET /tasks
 * Lista tareas de un proyecto. Las 3 columnas se cargan en una sola llamada
 * sin filtro de status — el frontend separa por columna (R-0403/R-0405).
 * @param {{
 *   project_id: string, priority?: string, status?: string, assigned_to?: string,
 *   due_date_from?: string, due_date_to?: string, search?: string,
 *   page?: number, page_size?: number
 * }} params
 * @returns {Promise<{ items: Task[], page: number, page_size: number, total: number, total_pages: number, next_page: number|null, previous_page: number|null, page_size_applied?: number }>}
 */
export async function fetchTasks({
  project_id,
  priority,
  status,
  assigned_to,
  due_date_from,
  due_date_to,
  search,
  page = 1,
  page_size = 50,
} = {}) {
  const params = new URLSearchParams({ project_id, page, page_size });
  if (priority) params.set("priority", priority);
  if (status) params.set("status", status);
  if (assigned_to) params.set("assigned_to", assigned_to);
  if (due_date_from) params.set("due_date_from", due_date_from);
  if (due_date_to) params.set("due_date_to", due_date_to);
  if (search?.trim()) params.set("search", search.trim());
  const { data } = await api.get(`/tasks?${params}`);
  return data;
}

/**
 * POST /tasks
 * @param {{ title: string, description?: string, priority: string, project_id: string, due_date?: string, assignee_ids?: string[] }} body
 * @returns {Promise<Task>}
 */
export async function createTask(body) {
  const { data } = await api.post("/tasks", body);
  return data;
}

/**
 * PATCH /tasks/{id}
 * @param {string} taskId
 * @param {{ title?: string, description?: string, priority?: string, due_date?: string, assignee_ids?: string[] }} body
 * @returns {Promise<Task>}
 */
export async function updateTask(taskId, body) {
  const { data } = await api.patch(`/tasks/${taskId}`, body);
  return data;
}

/**
 * PATCH /tasks/{id}/status
 * @param {string} taskId
 * @param {string} status abierto | en_proceso | completo
 * @returns {Promise<Task>}
 */
export async function updateTaskStatus(taskId, status) {
  const { data } = await api.patch(`/tasks/${taskId}/status`, { status });
  return data;
}

/**
 * PATCH /tasks/{id}/assignees
 * @param {string} taskId
 * @param {string[]} assigneeIds
 * @returns {Promise<Task>}
 */
export async function updateTaskAssignees(taskId, assigneeIds) {
  const { data } = await api.patch(`/tasks/${taskId}/assignees`, { assignee_ids: assigneeIds });
  return data;
}

/**
 * DELETE /tasks/{id}
 * Soft delete.
 * @param {string} taskId
 * @returns {Promise<void>}
 */
export async function deleteTask(taskId) {
  await api.delete(`/tasks/${taskId}`);
}

/**
 * @typedef {Object} TaskAssignee
 * @property {string}      id
 * @property {string}      username
 * @property {string|null} avatar
 * @property {boolean}     is_active
 *
 * @typedef {Object} Task
 * @property {string}          id
 * @property {number}          task_number
 * @property {string}          title
 * @property {string|null}     description
 * @property {"low"|"medium"|"high"} priority
 * @property {"abierto"|"en_proceso"|"completo"} status
 * @property {string}          project_id
 * @property {string}          created_by
 * @property {string|null}     due_date      YYYY-MM-DD
 * @property {boolean}         timer_disabled
 * @property {TaskAssignee[]}  assignees
 * @property {string}          created_at    ISO 8601
 * @property {string}          updated_at    ISO 8601
 */
