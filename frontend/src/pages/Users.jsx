import { useEffect, useState } from 'react';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { EmptyState, ErrorAlert, Loading, PageHeader, Pagination, SuccessAlert } from '../components/ui';
import { ROLE_LABELS, errorMessage, label } from '../utils';

const BLANK = { username: '', first_name: '', last_name: '', email: '', role: 'EMPLOYEE', department: '', job_title: '', employee_id: '', phone: '', password: '', is_active: true };

export default function Users() {
  const { user: me } = useAuth();
  const [filters, setFilters] = useState({ search: '', role: '', is_active: '' });
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ count: 0, results: [] });
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editing, setEditing] = useState(null); // null = closed, {} = new, {id...} = existing
  const [form, setForm] = useState(BLANK);
  const [formError, setFormError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get('/departments/').then((r) => setDepartments(r.data)).catch(() => {}); }, []);

  function load() {
    setLoading(true); setError('');
    api.get('/users/', { params: { page, search: filters.search || undefined, role: filters.role || undefined, is_active: filters.is_active || undefined } })
      .then((r) => setData(r.data)).catch((e) => setError(errorMessage(e))).finally(() => setLoading(false));
  }
  useEffect(() => {
    const timer = setTimeout(load, filters.search ? 350 : 0);
    return () => clearTimeout(timer);
  }, [filters, page]);

  function open(u) {
    setFormError('');
    setEditing(u || {});
    setForm(u ? { ...BLANK, ...Object.fromEntries(Object.keys(BLANK).map((k) => [k, u[k] ?? BLANK[k]])), password: '' } : BLANK);
  }

  async function save(e) {
    e.preventDefault();
    setBusy(true); setFormError('');
    const body = { ...form, department: form.department ? Number(form.department) : null, employee_id: form.employee_id || null };
    if (!body.password) delete body.password;
    try {
      if (editing.id) { delete body.username; await api.patch(`/users/${editing.id}/`, body); }
      else await api.post('/users/', body);
      setNotice(editing.id ? 'User updated.' : 'User created.');
      setEditing(null); load();
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(u) {
    const verb = u.is_active ? 'Deactivate' : 'Activate';
    if (!window.confirm(`${verb} ${u.full_name}?${u.is_active ? ' They will no longer be able to sign in.' : ''}`)) return;
    try { await api.patch(`/users/${u.id}/`, { is_active: !u.is_active }); setNotice(`${u.full_name} ${u.is_active ? 'deactivated' : 'activated'}.`); load(); }
    catch (err) { setError(errorMessage(err)); }
  }

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  return (
    <>
      <PageHeader title="Users" subtitle="Create accounts, set roles and departments, and deactivate people who leave.">
        <button className="btn btn-primary" onClick={() => open(null)}>Add user</button>
      </PageHeader>
      <SuccessAlert message={notice} onClose={() => setNotice('')} />

      {editing && (
        <div className="panel mb-3">
          <h2>{editing.id ? `Edit ${editing.username}` : 'New user'}</h2>
          <ErrorAlert message={formError} />
          <form onSubmit={save}>
            <div className="row">
              <div className="col-md-4 mb-3"><label className="form-label">Username</label><input className="form-control" required disabled={!!editing.id} value={form.username} onChange={set('username')} /></div>
              <div className="col-md-4 mb-3"><label className="form-label">First name</label><input className="form-control" value={form.first_name} onChange={set('first_name')} /></div>
              <div className="col-md-4 mb-3"><label className="form-label">Last name</label><input className="form-control" value={form.last_name} onChange={set('last_name')} /></div>
              <div className="col-md-4 mb-3"><label className="form-label">Email</label><input type="email" className="form-control" required value={form.email} onChange={set('email')} /></div>
              <div className="col-md-4 mb-3">
                <label className="form-label">Role</label>
                <select className="form-select" value={form.role} onChange={set('role')} disabled={editing.id === me.id}>
                  {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="col-md-4 mb-3">
                <label className="form-label">Department</label>
                <select className="form-select" value={form.department ?? ''} onChange={set('department')}>
                  <option value="">None</option>
                  {departments.filter((d) => d.is_active || d.id === editing.department).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
              <div className="col-md-4 mb-3"><label className="form-label">Job title</label><input className="form-control" value={form.job_title} onChange={set('job_title')} /></div>
              <div className="col-md-4 mb-3"><label className="form-label">Employee ID</label><input className="form-control" value={form.employee_id ?? ''} onChange={set('employee_id')} /></div>
              <div className="col-md-4 mb-3"><label className="form-label">Phone</label><input className="form-control" value={form.phone} onChange={set('phone')} /></div>
              <div className="col-md-6 mb-3">
                <label className="form-label">{editing.id ? 'New password (leave blank to keep the current one)' : 'Password'}</label>
                <input type="password" className="form-control" autoComplete="new-password" required={!editing.id} minLength={8} value={form.password} onChange={set('password')} />
              </div>
              <div className="col-md-6 mb-3 d-flex align-items-end">
                <div className="form-check"><input id="active" type="checkbox" className="form-check-input" checked={form.is_active} onChange={set('is_active')} disabled={editing.id === me.id} /><label htmlFor="active" className="form-check-label">Account is active</label></div>
              </div>
            </div>
            <button className="btn btn-primary me-2" disabled={busy}>{busy ? 'Saving…' : 'Save user'}</button>
            <button type="button" className="btn btn-light" onClick={() => setEditing(null)}>Cancel</button>
          </form>
        </div>
      )}

      <div className="panel">
        <div className="row g-2 mb-3">
          <div className="col-lg-6"><input className="form-control" aria-label="Search users" placeholder="Search by name, username, email or employee ID" value={filters.search} onChange={(e) => { setFilters({ ...filters, search: e.target.value }); setPage(1); }} /></div>
          <div className="col-6 col-lg-3">
            <select className="form-select" aria-label="Role" value={filters.role} onChange={(e) => { setFilters({ ...filters, role: e.target.value }); setPage(1); }}>
              <option value="">All roles</option>{Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div className="col-6 col-lg-3">
            <select className="form-select" aria-label="Account status" value={filters.is_active} onChange={(e) => { setFilters({ ...filters, is_active: e.target.value }); setPage(1); }}>
              <option value="">Active and inactive</option><option value="true">Active</option><option value="false">Inactive</option>
            </select>
          </div>
        </div>
        <ErrorAlert message={error} onRetry={load} />
        {loading ? <Loading /> : data.results.length === 0 ? <EmptyState title="No users match" /> : (
          <div className="table-responsive"><table className="table align-middle">
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Department</th><th>Status</th><th /></tr></thead>
            <tbody>{data.results.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name} <span className="text-muted">({u.username})</span></td>
                <td>{u.email}</td><td>{label(ROLE_LABELS, u.role)}</td><td>{u.department_name || '—'}</td>
                <td>{u.is_active ? <span className="pill asset-AVAILABLE">Active</span> : <span className="pill asset-RETIRED">Inactive</span>}</td>
                <td className="text-end text-nowrap">
                  <button className="btn btn-sm btn-outline-primary me-1" onClick={() => open(u)}>Edit</button>
                  {u.id !== me.id && <button className="btn btn-sm btn-outline-secondary" onClick={() => toggleActive(u)}>{u.is_active ? 'Deactivate' : 'Activate'}</button>}
                </td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
        <Pagination page={page} count={data.count} onChange={setPage} />
      </div>
    </>
  );
}
