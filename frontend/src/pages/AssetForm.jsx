import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { ErrorAlert, Loading, PageHeader } from '../components/ui';
import { errorMessage } from '../utils';

const EMPTY = {
  asset_tag: '', name: '', category: '', manufacturer: '', model_name: '', serial_number: '', purchase_date: '',
  purchase_price: '', warranty_expiry: '', department: '', location: '', notes: '',
};

/** Create (/assets/new) or edit (/assets/:id/edit) an asset. Admin only. */
export default function AssetForm() {
  const { id } = useParams();
  const nav = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [categories, setCategories] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const requests = [api.get('/asset-categories/'), api.get('/departments/')];
    if (id) requests.push(api.get(`/assets/${id}/`));
    Promise.all(requests).then(([c, d, a]) => {
      const activeCategories = c.data.filter((x) => x.is_active !== false);
      setCategories(a && a.data.category && !activeCategories.some((x) => x.id === a.data.category)
        ? [...activeCategories, c.data.find((x) => x.id === a.data.category)].filter(Boolean) : activeCategories);
      setDepartments(d.data.filter((x) => x.is_active));
      if (a) setForm(Object.fromEntries(Object.keys(EMPTY).map((k) => [k, a.data[k] ?? ''])));
      else if (activeCategories.length) setForm((f) => ({ ...f, category: String(activeCategories[0].id) }));
    }).catch((e) => setError(errorMessage(e))).finally(() => setLoading(false));
  }, [id]);

  async function submit(e) {
    e.preventDefault();
    setError(''); setBusy(true);
    const body = {
      ...form,
      category: Number(form.category),
      department: form.department ? Number(form.department) : null,
      purchase_date: form.purchase_date || null,
      warranty_expiry: form.warranty_expiry || null,
      purchase_price: form.purchase_price === '' ? null : form.purchase_price,
    };
    try {
      const { data } = id ? await api.patch(`/assets/${id}/`, body) : await api.post('/assets/', body);
      nav(`/assets/${data.id}`);
    } catch (err) {
      setError(errorMessage(err, 'Asset could not be saved.'));
      setBusy(false);
    }
  }

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const input = (key, text, props = {}) => (
    <div className="col-md-6 mb-3">
      <label className="form-label" htmlFor={key}>{text}</label>
      <input id={key} className="form-control" value={form[key]} onChange={set(key)} {...props} />
    </div>
  );

  if (loading) return <Loading />;
  return (
    <>
      <PageHeader title={id ? 'Edit asset' : 'Add asset'} subtitle="Status and assignment are changed with the actions on the asset page." />
      <div className="panel" style={{ maxWidth: 820 }}>
        <ErrorAlert message={error} />
        <form onSubmit={submit}>
          <div className="row">
            {input('asset_tag', 'Asset tag', { required: true, maxLength: 50, placeholder: 'e.g. LAP-0042' })}
            {input('name', 'Asset name', { maxLength: 150, placeholder: 'e.g. Dell Latitude 5440' })}
            <div className="col-md-6 mb-3">
              <label className="form-label" htmlFor="category">Category</label>
              <select id="category" className="form-select" required value={form.category} onChange={set('category')}>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}{c.is_active === false ? ' (inactive — existing asset)' : ''}</option>)}
              </select>
              {categories.length === 0 && <div className="form-text text-danger">Create an active asset category in Settings before adding assets.</div>}
            </div>
            <div className="col-md-6 mb-3">
              <label className="form-label" htmlFor="department">Department (optional)</label>
              <select id="department" className="form-select" value={form.department ?? ''} onChange={set('department')}>
                <option value="">None</option>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            {input('manufacturer', 'Manufacturer', { maxLength: 100 })}
            {input('model_name', 'Model', { maxLength: 100 })}
            {input('serial_number', 'Serial number', { maxLength: 100 })}
            {input('location', 'Location', { maxLength: 150 })}
            {input('purchase_date', 'Purchase date', { type: 'date' })}
            {input('warranty_expiry', 'Warranty expires', { type: 'date' })}
            {input('purchase_price', 'Purchase price', { type: 'number', min: 0, step: '0.01' })}
          </div>
          <label className="form-label" htmlFor="notes">Notes</label>
          <textarea id="notes" className="form-control mb-4" rows={3} value={form.notes} onChange={set('notes')} />
          <button className="btn btn-primary me-2" disabled={busy || categories.length === 0}>{busy ? 'Saving…' : 'Save asset'}</button>
          <Link className="btn btn-light" to={id ? `/assets/${id}` : '/assets'}>Cancel</Link>
        </form>
      </div>
    </>
  );
}
