import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { errorMessage } from '../utils';

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError(err.response?.status === 401 ? 'Username or password is incorrect.' : errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <h1>DeskPilot</h1>
        <p className="text-muted">Sign in to report a problem or manage support requests.</p>
        {error && <div className="alert alert-danger" role="alert">{error}</div>}
        <label className="form-label" htmlFor="username">Username</label>
        <input id="username" className="form-control mb-3" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required autoFocus />
        <label className="form-label" htmlFor="password">Password</label>
        <input id="password" type="password" className="form-control mb-3" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        <button className="btn btn-primary w-100" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <p className="small text-muted mt-3 mb-0">Need an account? Ask your IT administrator.</p>
      </form>
    </div>
  );
}
