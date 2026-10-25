import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/** Redirects anonymous users to /login. `roles` limits a page to certain roles (the backend enforces this too). */
export default function ProtectedRoute({ children, roles }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}
