import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Tickets from './pages/Tickets';
import CreateTicket from './pages/CreateTicket';
import TicketDetail from './pages/TicketDetail';
import Assets from './pages/Assets';
import AssetForm from './pages/AssetForm';
import AssetDetail from './pages/AssetDetail';
import Users from './pages/Users';
import Settings from './pages/Settings';
import Notifications from './pages/Notifications';

export default function App() {
  const { user, checking } = useAuth();
  if (checking) return <div className="loading-screen">Loading workspace…</div>;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/tickets" element={<Tickets />} />
        <Route path="/tickets/new" element={<CreateTicket />} />
        <Route path="/tickets/:id" element={<TicketDetail />} />
        <Route path="/assets" element={<Assets />} />
        <Route path="/assets/new" element={<ProtectedRoute roles={['ADMIN']}><AssetForm /></ProtectedRoute>} />
        <Route path="/assets/:id" element={<AssetDetail />} />
        <Route path="/assets/:id/edit" element={<ProtectedRoute roles={['ADMIN']}><AssetForm /></ProtectedRoute>} />
        <Route path="/users" element={<ProtectedRoute roles={['ADMIN']}><Users /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute roles={['ADMIN']}><Settings /></ProtectedRoute>} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
