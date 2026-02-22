import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import { ProtectedRoute } from './components/ProtectedRoute';
import { ProfessorLayout } from './layouts/ProfessorLayout';
import { StudentLayout } from './layouts/StudentLayout';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { PasswordResetPage } from './pages/PasswordResetPage';
import { PasswordResetConfirmPage } from './pages/PasswordResetConfirmPage';
import { DashboardPage } from './pages/DashboardPage';
import { UnauthorizedPage } from './pages/UnauthorizedPage';
import { ClassesListPage } from './pages/professor/ClassesListPage';
import { ClassDetailPage } from './pages/professor/ClassDetailPage';
import { ExercisesListPage } from './pages/professor/ExercisesListPage';
import { ExerciseFormPage } from './pages/professor/ExerciseFormPage';
import { ExerciseListBuilderPage } from './pages/professor/ExerciseListBuilderPage';
import { SubmissionReviewPage } from './pages/professor/SubmissionReviewPage';
import { GradesPage } from './pages/professor/GradesPage';
import { MessagingPage } from './pages/professor/MessagingPage';
import { CampaignDetailPage } from './pages/professor/CampaignDetailPage';
import { MyClassesPage } from './pages/student/MyClassesPage';
import { ExerciseListsViewPage } from './pages/student/ExerciseListsViewPage';
import { ExerciseDetailPage } from './pages/student/ExerciseDetailPage';
import { SubmissionResultsPage } from './pages/student/SubmissionResultsPage';
import { SubmissionDiffPage } from './pages/student/SubmissionDiffPage';
import { MyGradesPage } from './pages/student/MyGradesPage';
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
          <Route path="exercises/new" element={<ExerciseFormPage />} />
          <Route path="exercises/:id" element={<ExerciseFormPage />} />
          <Route path="exercises/:id/edit" element={<ExerciseFormPage />} />
          <Route path="classes/:classId/lists" element={<ExerciseListBuilderPage />} />
          <Route path="submissions/:id/review" element={<SubmissionReviewPage />} />
          <Route path="grades" element={<GradesPage />} />
          <Route path="messaging" element={<MessagingPage />} />
          <Route path="messaging/campaigns/:id" element={<CampaignDetailPage />} />
        </Route>

        {/* Student Dashboard */}
        <Route
          path="/student"
          element={
            <ProtectedRoute requiredRoles={['student']}>
              <StudentLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/student/classes" replace />} />
          <Route path="classes" element={<MyClassesPage />} />
          <Route path="classes/:classId/lists" element={<ExerciseListsViewPage />} />
          <Route path="exercises/:id" element={<ExerciseDetailPage />} />
          <Route path="submissions/:id" element={<SubmissionResultsPage />} />
          <Route path="submissions/:id/diff/:comparisonId" element={<SubmissionDiffPage />} />
          <Route path="grades" element={<MyGradesPage />} />
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
