import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export function DashboardPage() {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) {
      if (user.role === 'professor' || user.role === 'admin') {
        navigate('/professor/classes', { replace: true });
      } else if (user.role === 'student' || user.role === 'ta') {
        navigate('/student/classes', { replace: true });
      }
    }
  }, [user, navigate]);

  return (
    <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <p>Redirecting to your dashboard...</p>
    </div>
  );
}
