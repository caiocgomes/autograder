import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export function ProfessorLayout() {
  const { user, logout } = useAuthStore();
  const location = useLocation();

  const isActive = (path: string) => location.pathname.startsWith(path);

  const navItems = [
    { path: '/professor/classes', label: 'My Classes' },
    { path: '/professor/exercises', label: 'Exercises' },
    { path: '/professor/grades', label: 'Grades' },
    ...(user?.role === 'admin' ? [
      { path: '/professor/messaging', label: 'Mensagens' },
      { path: '/professor/onboarding', label: 'Onboarding' },
    ] : []),
  ];

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <aside
        style={{
          width: '250px',
          backgroundColor: '#2c3e50',
          color: 'white',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div style={{ marginBottom: '30px' }}>
          <h2 style={{ margin: 0, fontSize: '20px' }}>Autograder</h2>
          <p style={{ margin: '5px 0 0', fontSize: '12px', opacity: 0.7 }}>Professor Dashboard</p>
        </div>

        <nav style={{ flex: 1 }}>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {navItems.map((item) => (
              <li key={item.path} style={{ marginBottom: '10px' }}>
                <Link
                  to={item.path}
                  style={{
                    display: 'block',
                    padding: '10px 15px',
                    color: 'white',
                    textDecoration: 'none',
                    backgroundColor: isActive(item.path) ? '#34495e' : 'transparent',
                    borderRadius: '4px',
                    transition: 'background-color 0.2s',
                  }}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '20px' }}>
          <p style={{ margin: '0 0 10px', fontSize: '14px' }}>{user?.email}</p>
          <button
            onClick={logout}
            style={{
              width: '100%',
              padding: '8px',
              backgroundColor: '#e74c3c',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            Logout
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, padding: '30px', backgroundColor: '#ecf0f1' }}>
        <Outlet />
      </main>
    </div>
  );
}
