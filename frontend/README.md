# Kanban MVP — Frontend

SPA construida con **React + Vite + TailwindCSS + Zustand + React Query**.  
Parte del sistema Kanban MVP · PRD v2 · Stack: React 18 · TypeScript · Zustand · React Query · @dnd-kit · TailwindCSS · Vercel.

---

## Tabla de contenidos

1. [Prerrequisitos](#1-prerrequisitos)
2. [Variables de entorno](#2-variables-de-entorno)
3. [Setup local](#3-setup-local)
4. [Estructura del proyecto](#4-estructura-del-proyecto)
5. [Arquitectura de estado](#5-arquitectura-de-estado)
6. [Autenticación y bootstrap](#6-autenticación-y-bootstrap)
7. [Rutas y guards](#7-rutas-y-guards)
8. [Cliente HTTP y manejo de errores](#8-cliente-http-y-manejo-de-errores)
9. [Tablero Kanban y drag & drop](#9-tablero-kanban-y-drag--drop)
10. [Convenciones de desarrollo](#10-convenciones-de-desarrollo)
11. [Ejecutar tests](#11-ejecutar-tests)
12. [Deploy en Vercel](#12-deploy-en-vercel)
13. [Deuda técnica documentada](#13-deuda-técnica-documentada)

---

## 1. Prerrequisitos

| Herramienta | Versión mínima | Notas |
|---|---|---|
| Node.js | 20 LTS | Usar `nvm` o el instalador oficial |
| npm | 10 | Incluido con Node 20 |
| Git | cualquiera | |

El backend debe estar corriendo antes de levantar el frontend. Ver [README del backend](../backend/README.md).

```bash
# Verificar versiones
node --version   # debe ser >= 20.x
npm --version    # debe ser >= 10.x
```

---

## 2. Variables de entorno

Copia el archivo de ejemplo y edítalo:

```bash
cp .env.example .env.local
```

> **Nunca hagas commit de `.env.local`**. Ya está en `.gitignore`. El archivo `.env.example` sí se commitea.
>
> En Vite, solo las variables con prefijo `VITE_` son accesibles en el navegador. Nunca pongas secretos aquí — todo lo que definas es visible en el bundle final.

### Referencia completa de variables

```bash
# ─── API ──────────────────────────────────────────────────
VITE_API_URL=http://localhost:8000
# Producción: VITE_API_URL=https://kanban-api.up.railway.app
# Sin trailing slash. La app agrega la ruta: ${VITE_API_URL}/auth/login

# ─── Aplicación ───────────────────────────────────────────
VITE_APP_NAME=Kanban MVP
# Aparece en el <title> del documento y en la barra de navegación

VITE_ENV=development
# development | production
# En development se muestran errores detallados en la UI
```

### `.env.example` (archivo a commitear)

```bash
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=Kanban MVP
VITE_ENV=development
```

---

## 3. Setup local

Tiempo estimado: **menos de 3 minutos** desde cero.

### Paso 1 — Clonar e instalar dependencias

```bash
git clone https://github.com/tu-org/kanban-frontend.git
cd kanban-frontend
npm install
```

### Paso 2 — Configurar variables de entorno

```bash
cp .env.example .env.local
# Edita .env.local: ajusta VITE_API_URL si el backend corre en otro puerto
```

### Paso 3 — Verificar que el backend está activo

```bash
curl http://localhost:8000/health
# Esperado: {"status":"ok","db":"connected","timestamp":"..."}
```

### Paso 4 — Levantar el servidor de desarrollo

```bash
npm run dev
```

La app estará en: [http://localhost:5173](http://localhost:5173)

> **Puerto importante:** el backend tiene `CORS_ORIGINS=http://localhost:5173`. Si cambias el puerto de Vite, actualiza esa variable en el backend y reinícialo.

### Paso 5 — Verificar que todo funciona

Abre [http://localhost:5173](http://localhost:5173) en el navegador. Deberías ver la pantalla de login. Registra un usuario; el primer usuario registrado recibe el rol `admin` automáticamente (AG-01).

### Scripts disponibles

```bash
npm run dev          # Servidor de desarrollo con HMR
npm run build        # Build de producción en /dist
npm run preview      # Previsualizar el build de producción localmente
npm run lint         # ESLint sobre src/
npm run lint:fix     # ESLint con corrección automática
npm run type-check   # TypeScript sin emitir (tsc --noEmit)
npm run test         # Vitest (unitarios + integración ligera)
npm run test:ui      # Vitest con interfaz visual
npm run test:cov     # Vitest con reporte de cobertura
```

---

## 4. Estructura del proyecto

```
kanban-frontend/
│
├── public/
│   └── favicon.svg
│
├── src/
│   ├── main.tsx                  # Entry point: monta App en #root
│   ├── App.tsx                   # Router, QueryClientProvider, AuthBootstrap
│   │
│   ├── api/                      # Capa de acceso a la API — solo llamadas HTTP
│   │   ├── client.ts             # Instancia axios con interceptores (401 → refresh)
│   │   ├── auth.ts               # login, register, refresh, logout, forgotPassword, resetPassword
│   │   ├── users.ts              # getMe, updateMe, changePassword, getUsers, updateRole
│   │   ├── projects.ts           # CRUD proyectos, members, history, transferOwnership
│   │   ├── tasks.ts              # CRUD tareas, patchStatus, getFiltered
│   │   ├── timers.ts             # startTimer, stopTimer, getActiveTimer
│   │   ├── comments.ts           # getComments, createComment, deleteComment
│   │   └── dashboard.ts         # getDashboard
│   │
│   ├── store/                    # Estado global con Zustand (estado de cliente)
│   │   ├── authStore.ts          # accessToken (memoria), user, rol, setAuth, clearAuth
│   │   ├── timerStore.ts         # activeTaskId, elapsedSeconds, isRunning, tick
│   │   └── uiStore.ts            # sidebarOpen, activeProjectId, filtros activos del tablero
│   │
│   ├── hooks/                    # React Query hooks (estado de servidor)
│   │   ├── useAuth.ts            # useLogin, useRegister, useLogout, useBootstrap
│   │   ├── useProjects.ts        # useProjects, useProject, useCreateProject, ...
│   │   ├── useTasks.ts           # useTasks, useTask, useCreateTask, usePatchStatus, ...
│   │   ├── useMembers.ts         # useMembers, useAddMember, useRemoveMember, ...
│   │   ├── useTimer.ts           # useStartTimer, useStopTimer, useActiveTimer
│   │   ├── useComments.ts        # useComments, useCreateComment, useDeleteComment
│   │   ├── useDashboard.ts       # useDashboard
│   │   └── useUsers.ts           # useUsers, useUpdateRole (admin)
│   │
│   ├── components/               # Componentes reutilizables
│   │   ├── ui/                   # Primitivos: Button, Input, Modal, Badge, Avatar, Spinner...
│   │   ├── layout/               # Sidebar, Navbar, PageShell, MobileMenu
│   │   ├── auth/                 # LoginForm, RegisterForm, VerifyEmailForm, ResetPasswordForm
│   │   ├── projects/             # ProjectCard, ProjectForm, MemberList, TransferOwnershipModal
│   │   ├── tasks/                # TaskCard, TaskForm, TaskDetail, AssigneeSelector, PriorityBadge
│   │   ├── kanban/               # KanbanBoard, KanbanColumn, DraggableCard, EmptyColumn
│   │   ├── timer/                # TimerButton, TimerDisplay, TimerHistory
│   │   ├── dashboard/            # MetricCard, PriorityChart, StatusChart, TimeByProject
│   │   └── admin/                # UserTable, RoleSelector, AuditLogTable
│   │
│   ├── pages/                    # Una carpeta por ruta de nivel superior
│   │   ├── auth/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   ├── VerifyEmailPage.tsx
│   │   │   ├── ForgotPasswordPage.tsx
│   │   │   └── ResetPasswordPage.tsx
│   │   ├── projects/
│   │   │   ├── ProjectsPage.tsx      # Listado de proyectos
│   │   │   └── ProjectDetailPage.tsx # Tablero Kanban del proyecto
│   │   ├── profile/
│   │   │   └── ProfilePage.tsx
│   │   ├── dashboard/
│   │   │   └── DashboardPage.tsx
│   │   └── admin/
│   │       ├── UsersPage.tsx
│   │       └── AuditLogsPage.tsx
│   │
│   ├── router/
│   │   ├── index.tsx             # createBrowserRouter con todas las rutas
│   │   ├── ProtectedRoute.tsx    # Guard: redirige a /login si no hay sesión
│   │   ├── PublicOnlyRoute.tsx   # Guard: redirige a /projects si ya hay sesión
│   │   └── AdminRoute.tsx        # Guard: redirige a /projects si rol !== admin
│   │
│   ├── lib/
│   │   ├── queryClient.ts        # Instancia de QueryClient con defaults
│   │   ├── axios.ts              # Re-export del client con tipos
│   │   └── timezone.ts           # Detecta timezone con Intl.DateTimeFormat (AG-02)
│   │
│   ├── types/
│   │   ├── api.ts                # Tipos de request/response que replica el OpenAPI del backend
│   │   ├── auth.ts
│   │   ├── task.ts
│   │   ├── project.ts
│   │   └── pagination.ts        # PaginatedResponse<T>
│   │
│   └── utils/
│       ├── formatTime.ts         # segundos → "2h 34m", timestamp → fecha localizada
│       ├── errorMessage.ts       # Extrae error.message del response de la API
│       └── cn.ts                 # clsx + tailwind-merge helper
│
├── .env.example
├── .gitignore
├── eslint.config.js
├── index.html
├── package.json
├── tailwind.config.ts
├── tsconfig.json
├── tsconfig.app.json
└── vite.config.ts
```

---

## 5. Arquitectura de estado

El frontend separa dos tipos de estado con herramientas distintas. Esta separación evita el boilerplate de Redux y elimina la necesidad de gestionar loading/error/caché manualmente.

### Zustand — estado de cliente

Persiste en memoria durante la sesión. Se pierde al recargar (intencional para seguridad de tokens).

```
authStore
  accessToken: string | null    ← JWT en memoria, NUNCA en localStorage
  user: User | null
  setAuth(token, user) → void
  clearAuth() → void

timerStore
  activeTaskId: string | null   ← id de la tarea con timer corriendo
  elapsedSeconds: number        ← contador local sincronizado con el backend al montar
  isRunning: boolean
  tick() → void                 ← llamado por setInterval cada segundo

uiStore
  activeProjectId: string | null
  sidebarOpen: boolean
  boardFilters: BoardFilters     ← filtros activos del tablero Kanban
```

> **Regla crítica de seguridad:** el `accessToken` vive únicamente en `authStore`. Jamás se escribe en `localStorage`, `sessionStorage`, ni en ningún atributo del DOM. Si se necesita persistir la sesión entre recargas, se usa el refresh token (cookie HttpOnly gestionada por el backend).

### React Query — estado de servidor

Gestiona el ciclo de vida de los datos remotos: fetching, caché, invalidación, reintento y sincronización en background.

```typescript
// Configuración global en src/lib/queryClient.ts
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2,     // 2 minutos antes de refetch en background
      retry: 1,                       // 1 reintento ante errores de red
      refetchOnWindowFocus: false,    // No refetch al cambiar de tab (AG-05 — timer)
    },
  },
})
```

**Query keys por dominio:**

```typescript
// Convención: arrays jerárquicos para invalidación precisa
['projects']                          // lista de proyectos
['projects', projectId]               // un proyecto específico
['tasks', { projectId, ...filters }]  // tareas con sus filtros
['tasks', taskId]                     // una tarea específica
['members', projectId]                // miembros de un proyecto
['timer', 'active']                   // timer activo del usuario
['dashboard']                         // métricas del dashboard
['users']                             // lista de usuarios (admin)
```

---

## 6. Autenticación y bootstrap

### Flujo de bootstrap (al montar la app)

Al iniciar React, antes de renderizar cualquier ruta protegida, la app ejecuta el bootstrap de autenticación:

```
App monta
  └── AuthBootstrap ejecuta POST /auth/refresh (credentials: include)
        ├── 200 OK → guarda accessToken en authStore → renderiza app autenticada
        ├── 401    → clearAuth() → muestra pantalla de login
        └── 5xx    → muestra pantalla de error de conexión con botón "Reintentar"
```

**Reglas del bootstrap:**
- Timeout de 5 segundos. Si excede → tratar como error de red.
- 1 reintento automático ante error de red; sin retry ante 401/403.
- Muestra un loading global (spinner centrado) mientras dura el proceso. No renderiza rutas hasta completar.
- Como el refresh token no rota (ADR-01), múltiples pestañas ejecutando el bootstrap concurrentemente no generan conflictos.

### Interceptor 401 durante la sesión

Cuando cualquier request a la API retorna 401 (token expirado):

```
Request falla con 401
  └── Interceptor ejecuta POST /auth/refresh
        ├── 200 OK → actualiza accessToken en authStore → reintenta request original (1 vez)
        └── 401    → clearAuth() → navega a /login
```

El interceptor está en `src/api/client.ts` usando un interceptor de respuesta de axios. Solo se permite **1 reintento** por request para evitar loops infinitos.

### Resincronización al recuperar foco de ventana

Cuando el usuario vuelve a la pestaña después de estar en otro lado:

```typescript
// En AuthBootstrap o en un hook de nivel superior
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    // Resincronizar el timer activo con el backend
    queryClient.invalidateQueries({ queryKey: ['timer', 'active'] })
  }
})
```

### Flujo de login

```
Usuario ingresa credenciales
  └── POST /auth/login
        ├── 200 OK → { accessToken, user } → authStore.setAuth() → navega a /projects
        ├── 401    → muestra "Email o contraseña incorrectos"
        └── 403    → muestra "Email no verificado. Revisa tu bandeja de entrada."
```

### Detección automática de timezone en registro (AG-02)

```typescript
// src/lib/timezone.ts
export function detectTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch {
    return 'UTC'  // fallback si el navegador no soporta la API
  }
}
```

Se llama en `RegisterForm` y se incluye en el body del `POST /auth/register`. El usuario puede cambiarlo después desde su perfil.

---

## 7. Rutas y guards

### Mapa de rutas

```
/                          → redirige a /projects (si autenticado) o /login
/login                     → PublicOnlyRoute → LoginPage
/register                  → PublicOnlyRoute → RegisterPage
/verify-email              → PublicOnlyRoute → VerifyEmailPage
/forgot-password           → PublicOnlyRoute → ForgotPasswordPage
/reset-password            → PublicOnlyRoute → ResetPasswordPage

/projects                  → ProtectedRoute → ProjectsPage
/projects/:id              → ProtectedRoute → ProjectDetailPage (tablero Kanban)
/profile                   → ProtectedRoute → ProfilePage
/dashboard                 → ProtectedRoute → DashboardPage

/admin/users               → AdminRoute → UsersPage
/admin/audit-logs          → AdminRoute → AuditLogsPage
```

### Guards

**`ProtectedRoute`** — verifica que `authStore.user !== null`. Si no hay sesión, redirige a `/login` preservando la URL de origen:

```typescript
// Al completar el login exitosamente:
const from = location.state?.from?.pathname ?? '/projects'
navigate(from, { replace: true })
```

**`PublicOnlyRoute`** — verifica que el usuario **no** esté autenticado. Si ya tiene sesión activa, redirige a `/projects`. Evita que un usuario logueado acceda a `/login`.

**`AdminRoute`** — extiende `ProtectedRoute`. Además verifica que `authStore.user.role === 'admin'`. Si el rol es insuficiente, redirige a `/projects` (no muestra 403 explícito para no revelar la existencia de la ruta).

### Visibilidad de UI por rol

Los guards protegen rutas completas. Dentro de las páginas, la UI adapta lo que muestra según el rol:

| Elemento | viewer | editor | admin |
|---|---|---|---|
| Botón "Crear tarea" | ✗ | ✓ | ✓ |
| Botón "Remover miembro" | ✗ | ✓ (si es owner del proyecto) | ✓ |
| Filtro `assigned_to=all` | ✗ | ✓ | ✓ |
| Historial de tiempo del equipo | ✗ | ✓ | ✓ |
| Menú de admin (usuarios, logs) | ✗ | ✗ | ✓ |
| Transferir ownership | solo si es owner | ✗ | ✓ |

> **Regla:** la UI solo oculta elementos para mejorar la UX. La autorización real ocurre siempre en el backend. No depender de la UI para seguridad.

---

## 8. Cliente HTTP y manejo de errores

### Instancia de axios (`src/api/client.ts`)

```typescript
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: false,   // false por defecto; true solo en /auth/refresh
})

// Request interceptor: inyecta el accessToken en cada request
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

> `withCredentials: true` se activa **solo** en la llamada a `POST /auth/refresh` para enviar la cookie HttpOnly. El resto de los endpoints no la necesitan.

### Formato de errores del backend

El backend siempre responde con:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Email o contraseña incorrectos.",
    "details": null
  }
}
```

El helper `src/utils/errorMessage.ts` extrae el mensaje legible para mostrar en la UI:

```typescript
export function getErrorMessage(error: unknown, fallback = 'Ocurrió un error inesperado.'): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.error?.message ?? fallback
  }
  return fallback
}
```

### Manejo de errores en React Query

```typescript
// En cada hook de mutación, el error se expone para mostrar en el formulario:
const { mutate: login, error, isPending } = useMutation({
  mutationFn: (credentials) => api.auth.login(credentials),
  onSuccess: (data) => {
    authStore.setAuth(data.accessToken, data.user)
    navigate('/projects')
  },
})

// En el componente:
{error && <p className="text-red-600 text-sm">{getErrorMessage(error)}</p>}
```

---

## 9. Tablero Kanban y drag & drop

### Librería: `@dnd-kit/core` + `@dnd-kit/sortable`

Se eligió `@dnd-kit` sobre react-beautiful-dnd por ser la librería más activa y mantenida actualmente, con soporte nativo para accesibilidad (teclado y lectores de pantalla).

### Estructura de componentes

```
KanbanBoard
  ├── DndContext (sensors, onDragEnd)
  ├── KanbanColumn status="abierto"
  │     ├── SortableContext
  │     ├── DraggableCard (por cada tarea)
  │     └── EmptyColumn (si no hay tareas)
  ├── KanbanColumn status="en_proceso"
  └── KanbanColumn status="completo"
```

### Flujo de drag & drop con optimistic update

```
Usuario suelta tarjeta en columna destino
  └── onDragEnd captura { taskId, newStatus }
        ├── Optimistic update: actualiza la lista local en React Query cache
        │     queryClient.setQueryData(['tasks', ...], (old) => updateStatus(old, taskId, newStatus))
        └── PATCH /tasks/{taskId}/status { status: newStatus }
              ├── 200 OK → invalida ['tasks', ...] para sincronizar con el servidor
              └── Error  → rollback: restaura el estado anterior en el cache
```

```typescript
// Implementación simplificada en KanbanBoard.tsx
function onDragEnd(event: DragEndEvent) {
  const { active, over } = event
  if (!over || active.id === over.id) return

  const taskId = active.id as string
  const newStatus = over.id as TaskStatus   // el id del drop container es el status

  // 1. Optimistic update
  const previousData = queryClient.getQueryData(['tasks', filters])
  queryClient.setQueryData(['tasks', filters], optimisticallyUpdateStatus(taskId, newStatus))

  // 2. Mutación
  patchStatus({ taskId, status: newStatus }, {
    onError: () => {
      // 3. Rollback si el servidor rechaza
      queryClient.setQueryData(['tasks', filters], previousData)
      toast.error('No se pudo mover la tarea. Inténtalo de nuevo.')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}
```

### Columnas vacías y estados de carga

- Las **3 columnas siempre son visibles** independientemente de los filtros activos (DU-03).
- Columna sin tareas **sin filtro activo**: muestra CTA "＋ Crear primera tarea" (AG-03). Solo visible para editores y admins.
- Columna sin tareas **con filtro activo**: muestra "Sin tareas con este filtro" con ícono neutral, sin CTA.
- Las zonas de drop permanecen activas aunque la columna esté vacía (para arrastrar hacia columnas vacías).
- El componente `EmptyColumn` recibe el prop `isFiltered: boolean` para seleccionar el contenido correcto.

### Badge "Miembro removido" (DU-01)

Cada tarea incluye en su respuesta el array `assignees[{ id, username, avatar, is_active }]`. Si `is_active = false`, la tarjeta muestra el avatar del asignado con un badge rojo "Removido" para que el equipo sepa que esa tarea tiene un asignado que ya no pertenece al proyecto.

### Regla del cronómetro en tareas con múltiples asignados (ADR-03)

Si `task.timer_disabled === true` (2 o más asignados), el botón de timer aparece deshabilitado con tooltip: "El cronómetro no está disponible para tareas con múltiples asignados."

---

## 10. Convenciones de desarrollo

### Estructura de un componente

```typescript
// Orden recomendado dentro de cada archivo de componente:
// 1. Imports
// 2. Types/interfaces locales
// 3. El componente (función nombrada, no arrow function en export default)
// 4. export default

// ✅ Correcto
function TaskCard({ task, onEdit }: TaskCardProps) {
  // hooks primero
  const { mutate: patchStatus } = usePatchStatus()
  // luego lógica
  // luego JSX
}
export default TaskCard

// ❌ Evitar
export default function({ task }) { ... }  // sin nombre dificulta el stack trace
```

### Nomenclatura

| Elemento | Convención | Ejemplo |
|---|---|---|
| Componentes | PascalCase | `TaskCard.tsx` |
| Hooks | camelCase con prefijo `use` | `useTasks.ts` |
| Stores | camelCase con sufijo `Store` | `authStore.ts` |
| Utilidades | camelCase | `formatTime.ts` |
| Tipos | PascalCase | `TaskResponse` |
| Constantes | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` |

### Prohibiciones explícitas (seguridad)

```typescript
// ❌ NUNCA — el token se puede robar con XSS
localStorage.setItem('accessToken', token)
sessionStorage.setItem('accessToken', token)
document.cookie = `accessToken=${token}`

// ✅ SIEMPRE — solo en memoria Zustand
useAuthStore.getState().setAuth(token, user)
```

### Tailwind: clases dinámicas

Usar el helper `cn` (clsx + tailwind-merge) para combinar clases condicionalmente:

```typescript
import { cn } from '@/utils/cn'

// ✅ Correcto — tailwind-merge resuelve conflictos
<div className={cn('px-4 py-2', isActive && 'bg-blue-500', className)} />

// ❌ Evitar — puede generar clases duplicadas o conflictivas
<div className={`px-4 py-2 ${isActive ? 'bg-blue-500' : ''}`} />
```

### Ramas

```
main         → producción (Vercel deploya desde aquí)
develop      → integración de features
feature/xxx  → nueva funcionalidad
fix/xxx      → corrección de bug
```

### Pull Requests

Un PR no puede mergearse si:

- ESLint reporta errores (`npm run lint`)
- TypeScript reporta errores (`npm run type-check`)
- Los tests fallan (`npm run test`)
- Falta al menos un revisor aprobador (Frontend o UX/UI)

### Definition of Done (componentes de UI)

Un componente se considera **Done** cuando:

1. Funciona correctamente en Chrome, Firefox y Safari (escritorio y móvil)
2. Tiene estados de loading, error y vacío implementados
3. Pasa la revisión de UX con los wireframes acordados
4. No hay `any` explícitos en TypeScript sin comentario justificado
5. No hay `console.log` sin eliminar
6. Funciona correctamente con teclado (tab, enter, escape en modales)

---

## 11. Ejecutar tests

### Stack de testing

| Herramienta | Propósito |
|---|---|
| Vitest | Test runner (reemplaza Jest, integrado con Vite) |
| React Testing Library | Renderizar componentes en tests |
| MSW (Mock Service Worker) | Interceptar llamadas a la API en tests |
| @testing-library/user-event | Simular interacciones de usuario |

### Comandos

```bash
# Todos los tests (una sola ejecución)
npm run test

# Modo watch (durante desarrollo)
npm run test -- --watch

# Con interfaz visual de Vitest
npm run test:ui

# Con reporte de cobertura
npm run test:cov

# Un archivo específico
npm run test -- src/components/auth/LoginForm.test.tsx

# Tests que coincidan con un patrón
npm run test -- --reporter=verbose -t "LoginForm"
```

### Organización de tests

```
src/
├── components/
│   └── auth/
│       ├── LoginForm.tsx
│       └── LoginForm.test.tsx     ← tests junto al componente
├── hooks/
│   └── useAuth.test.ts
└── utils/
    └── formatTime.test.ts
```

### Qué testear

```typescript
// ✅ Testear comportamiento observable desde el usuario
test('muestra error cuando las credenciales son incorrectas', async () => {
  server.use(
    http.post('/auth/login', () => HttpResponse.json(
      { error: { code: 'INVALID_CREDENTIALS', message: 'Email o contraseña incorrectos.' } },
      { status: 401 }
    ))
  )
  render(<LoginForm />)
  await userEvent.type(screen.getByLabelText('Email'), 'user@test.com')
  await userEvent.type(screen.getByLabelText('Contraseña'), 'wrongpassword')
  await userEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
  expect(await screen.findByText('Email o contraseña incorrectos.')).toBeInTheDocument()
})

// ❌ No testear detalles de implementación
test('llama a axios.post con los parámetros correctos', ...)  // frágil, no aporta valor
```

### Cobertura mínima requerida

| Módulo | Cobertura mínima |
|---|---|
| `src/store/` | 80% |
| `src/utils/` | 90% |
| `src/components/auth/` | 75% |
| `src/hooks/` | 70% |

---

## 12. Deploy en Vercel

### Configuración del proyecto en Vercel

1. Conecta el repositorio en [vercel.com](https://vercel.com)
2. Framework preset: **Vite**
3. Build command: `npm run build`
4. Output directory: `dist`
5. Install command: `npm install`

### Variables de entorno en Vercel

Configurar en **Vercel → Project → Settings → Environment Variables**:

```
VITE_API_URL     = https://kanban-api.up.railway.app
VITE_APP_NAME    = Kanban MVP
VITE_ENV         = production
```

> Asegúrate de que el valor de `VITE_API_URL` coincida **exactamente** con el dominio configurado en `CORS_ORIGINS` del backend. Sin trailing slash.

### Archivo `vercel.json` (necesario para SPA con React Router)

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

Sin este archivo, al recargar la página en cualquier ruta que no sea `/` Vercel retorna 404 porque no existe el archivo físico.

### Verificación post-deploy

```bash
# Verificar que el build funciona localmente antes de hacer push
npm run build
npm run preview
# Abre http://localhost:4173 y navega a una ruta protegida, recarga, y verifica que no da 404
```

---

## 13. Deuda técnica documentada

Decisiones tomadas conscientemente para el MVP. No implementar sin consenso del equipo.

| ID | Descripción | Sprint origen | Para resolver |
|---|---|---|---|
| **DT-FE-01** | El interceptor 401 puede generar condiciones de carrera si dos requests fallan simultáneamente y ambas intentan hacer el refresh al mismo tiempo. La implementación actual serializa el refresh con una variable de bloqueo en memoria, pero no es infalible con múltiples tabs. | S1 | Resolver con BroadcastChannel para coordinar el refresh entre tabs en post-MVP. |
| **DT-FE-02** | `refetchOnWindowFocus: false` en React Query para evitar conflictos con el timer activo (el refetch podía resetear el contador visual). Si se activa en el futuro, hay que sincronizar el timer antes del refetch. | S1 | Evaluar en S4 cuando el timer esté completo. |
| **DT-FE-03** | La paginación del tablero Kanban carga máximo 50 tareas por columna. Si un proyecto tiene más, el usuario ve una nota "Mostrando primeras 50 tareas". No hay scroll infinito en MVP. | S3 | Implementar scroll infinito por columna en post-MVP con `useInfiniteQuery`. |
| **DT-FE-04** | FTS (búsqueda) usa debounce de 400ms en el input. Si la conexión es lenta, el usuario puede ver resultados desincronizados momentáneamente. | S3 | Aceptable para MVP. |
| **DT-FE-05** | Sin Progressive Web App (PWA). La app no funciona offline. | S1 | Evaluar según necesidades del cliente en post-MVP. |

---

## Épicas cubiertas por sprint

| Sprint | Épicas | Estado |
|---|---|---|
| S1 | E01 Auth + E09 Infra base | ✅ |
| S2 | E02 Roles + E03 Proyectos (sin invitaciones) | 🔄 En progreso |
| S3 | E04 Tareas y Kanban | ⏳ |
| S4 | E05 Cronómetro + E03 Invitaciones | ⏳ |
| S5 | E06 Dashboard + E07 Comentarios | ⏳ |
| S6 | E08 Auditoría + E09 Admin + E02 Admin | ⏳ |
| S7 | QA + Deploy producción | ⏳ |

---

*Kanban MVP Frontend · PRD v2 · React 18 · TypeScript · Zustand · React Query · @dnd-kit · TailwindCSS · Vercel · 56 requerimientos · 9 épicas*
