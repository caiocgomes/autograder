import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import { ProtectedRoute } from './components/ProtectedRoute';
import { ProfessorLayout } from './layouts/ProfessorLayout';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { PasswordResetPage } from './pages/PasswordResetPage';
import { PasswordResetConfirmPage } from './pages/PasswordResetConfirmPage';
import { DashboardPage } from './pages/DashboardPage';
import { UnauthorizedPage } from './pages/UnauthorizedPage';
import { ClassesListPage } from './pages/professor/ClassesListPage';
import { ClassDetailPage } from './pages/professor/ClassDetailPage';
import { ExercisesListPage } from './pages/professor/ExercisesListPage';
import { GradesPage } from './pages/professor/GradesPage';
import './App.css';

function App() {
  const { loadUser } = useAuthStore();

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/password-reset" element={<PasswordResetPage />} />
        <Route path="/password-reset/confirm" element={<PasswordResetConfirmPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />

        {/* Professor Dashboard */}
        <Route
          path="/professor"
          element={
            <ProtectedRoute requiredRoles={['professor', 'admin']}>
              <ProfessorLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/professor/classes" replace />} />
          <Route path="classes" element={<ClassesListPage />} />
          <Route path="classes/:id" element={<ClassDetailPage />} />
          <Route path="exercises" element={<ExercisesListPage />} />
          <Route path="grades" element={<GradesPage />} />
        </Route>

        {/* Generic Dashboard (redirects based on role) */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
