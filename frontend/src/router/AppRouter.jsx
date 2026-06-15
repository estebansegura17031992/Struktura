import { Routes, Route, Navigate } from "react-router-dom";
import PrivateRoute       from "./PrivateRoute";
import PublicRoute        from "./PublicRoute";
import AdminRoute         from "./AdminRoute";
import RegisterPage       from "@/pages/auth/RegisterPage";
import LoginPage          from "@/pages/auth/LoginPage";
import VerifyEmailPage    from "@/pages/auth/VerifyEmailPage";
import ForgotPasswordPage from "@/pages/auth/ForgotPasswordPage";
import ResetPasswordPage  from "@/pages/auth/ResetPasswordPage";
import ProfilePage        from "@/pages/profile/ProfilePage";
import AdminUsersPage     from "@/pages/admin/AdminUsersPage";
import ProjectsPage       from "@/pages/projects/ProjectsPage";
import ProjectMembersPage from "@/pages/projects/ProjectMembersPage";

const Placeholder = ({ label }) => (
  <div className="min-h-screen bg-background flex items-center justify-center">
    <div className="bg-surface-container border border-outline-variant/30 rounded-xl p-8 text-center max-w-sm">
      <span className="material-symbols-outlined text-primary text-[40px] mb-3 block">construction</span>
      <p className="font-['Poppins'] text-lg font-semibold text-on-surface mb-1">{label}</p>
      <p className="text-sm text-on-surface-variant">Pendiente de implementación</p>
    </div>
  </div>
);

const AppRouter = () => (
  <Routes>
    {/* Públicas */}
    <Route element={<PublicRoute />}>
      <Route path="/register"        element={<RegisterPage />} />
      <Route path="/login"           element={<LoginPage />} />
      <Route path="/verify-email"    element={<VerifyEmailPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password"  element={<ResetPasswordPage />} />
    </Route>

    {/* Privadas */}
    <Route element={<PrivateRoute />}>
      <Route path="/dashboard"                      element={<Placeholder label="Dashboard — Sprint 3" />} />
      <Route path="/profile"                        element={<ProfilePage />} />
      <Route path="/projects"                       element={<ProjectsPage />} />
      <Route path="/projects/:projectId/members"    element={<ProjectMembersPage />} />
    </Route>

    {/* Admin */}
    <Route element={<AdminRoute />}>
      <Route path="/admin/users" element={<AdminUsersPage />} />
    </Route>

    {/* Fallbacks — siempre al final */}
    <Route path="/"  element={<Navigate to="/login" replace />} />
    <Route path="*"  element={<Navigate to="/login" replace />} />
  </Routes>
);

export default AppRouter;