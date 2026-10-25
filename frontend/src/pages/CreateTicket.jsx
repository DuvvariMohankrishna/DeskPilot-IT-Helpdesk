import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { ErrorAlert, Loading, PageHeader } from '../components/ui';
import { PRIORITY_LABELS, errorMessage, unwrap } from '../utils';

export default function CreateTicket() {
  const nav = useNavigate();
  const { isStaff, isAdmin } = useAuth();
  const [categories, setCategories] = useState(null);
  const [assets, setAssets] = useState([]);
  const [form, setForm] = useState({ title: '', description: '', category: '', priority: 'MEDIUM', asset: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get('/ticket-categories/')
      .then((r) => { setCategories(r.data); if (r.data.length) setForm((f) => ({ ...f, category: String(r.data[0].id) })); })
      .catch((e) => { setCategories([]); setError(errorMessage(e, 'Could not load categories.')); });
    // employees can only link equipment assigned to them; staff link assets from the ticket page
    if (!isStaff) api.get('/assets/', { params: { page_size: 100 } }).then((r) => setAssets(unwrap(r))).catch(() => {});
  }, [isStaff]);

  async function submit(e) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      const body = { ...form, category: Number(form.category), asset: form.asset ? Number(form.asset) : null };
      const { data } = await api.post('/tickets/', body);
      nav(`/tickets/${data.id}`, { state: { created: data.ticket_number } });
    } catch (err) {
      setError(errorMessage(err, 'Ticket could not be created.'));
      setBusy(false);
    }
  }

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  if (!categories) return <Loading />;

  return (
    <>
      <PageHeader title="Create ticket" subtitle="Describe the problem so IT can help quickly." />
      <div className="panel" style={{ maxWidth: 760 }}>
        <ErrorAlert message={error} />
        {categories.length === 0 ? (
          <div className="alert alert-warning mb-0">
            No ticket categories exist yet. {isAdmin
              ? <>Add some under <Link to="/settings">Departments &amp; categories</Link>, or run <code>python manage.py seed_data</code>.</>
              : 'Please ask an administrator to set up ticket categories.'}
          </div>
        ) : (
          <form onSubmit={submit}>
            <label className="form-label" htmlFor="title">Title</label>
            <input id="title" className="form-control mb-3" required minLength={5} maxLength={200} value={form.title} onChange={set('title')} placeholder="e.g. Laptop will not connect to office Wi-Fi" />
            <label className="form-label" htmlFor="description">What is happening?</label>
            <textarea id="description" className="form-control mb-3" rows={5} required minLength={10} value={form.description} onChange={set('description')} placeholder="What you were doing, what you expected, and any error message." />
            <div className="row">
              <div className="col-md-6 mb-3">
                <label className="form-label" htmlFor="category">Category</label>
                <select id="category" className="form-select" required value={form.category} onChange={set('category')}>
                  {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="col-md-6 mb-3">
                <label className="form-label" htmlFor="priority">Priority</label>
                <select id="priority" className="form-select" value={form.priority} onChange={set('priority')}>
                  {Object.entries(PRIORITY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
            </div>
            {!isStaff && (
              <div className="mb-4">
                <label className="form-label" htmlFor="asset">Related equipment (optional)</label>
                <select id="asset" className="form-select" value={form.asset} onChange={set('asset')}>
                  <option value="">Not about a specific device</option>
                  {assets.map((a) => <option key={a.id} value={a.id}>{a.asset_tag} · {a.name || [a.manufacturer, a.model_name].join(' ')}</option>)}
                </select>
              </div>
            )}
            <button className="btn btn-primary me-2" disabled={busy}>{busy ? 'Submitting…' : 'Submit ticket'}</button>
            <Link className="btn btn-light" to="/tickets">Cancel</Link>
          </form>
        )}
      </div>
    </>
  );
}
