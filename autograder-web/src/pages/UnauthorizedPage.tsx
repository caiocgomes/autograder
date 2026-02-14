import { useNavigate } from 'react-router-dom';

export function UnauthorizedPage() {
  const navigate = useNavigate();

  return (
    <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <h1>403 - Unauthorized</h1>
      <p>You don't have permission to access this page.</p>
      <button onClick={() => navigate(-1)}>Go Back</button>
    </div>
  );
}
