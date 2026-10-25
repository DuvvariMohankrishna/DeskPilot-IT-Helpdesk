import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { AssetStatusBadge, EmptyState, ErrorAlert, Loading, PageHeader, Pagination } from '../components/ui';
import { ASSET_STATUS_LABELS, errorMessage, formatDate } from '../utils';

export default function Assets() {
  const { isAdmin, isStaff } = useAuth();
  const [params] = useSearchParams();
  const [filters, setFilters] = useState({ search: '', status: params.get('status') || '', category: '' });
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState([]);
  const [data, setData] = useState({ count: 0, results: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => { api.get('/asset-categories/').then((r) => setCategories(r.data)).catch(() => {}); }, []);

  function load() {
    setLoading(true); setError('');
    api.get('/assets/', { params: { page, search: filters.search || undefined, status: filters.status || undefined, category: filters.category || undefined } })
      .then((r) => setData(r.data))
      .catch((e) => setError(errorMessage(e, 'Unable to load assets.')))
      .finally(() => setLoading(false));
  }
  useEffect(() => {
    const timer = setTimeout(load, filters.search ? 350 : 0);
    return () => clearTimeout(timer);
  }, [filters, page]);

  const set = (key) => (e) => { setFilters({ ...filters, [key]: e.target.value }); setPage(1); };
  const hasFilters = filters.search || filters.status || filters.category;

  return (
    <>
      <PageHeader title={isStaff ? 'Assets' : 'My assets'} subtitle={isStaff ? 'Hardware inventory and who holds each item.' : 'Equipment currently assigned to you.'}>
        {isAdmin && <Link className="btn btn-primary" to="/assets/new">Add asset</Link>}
      </PageHeader>
      <div className="panel">
        {isStaff && (
          <div className="row g-2 mb-3">
            <div className="col-lg-6"><input className="form-control" aria-label="Search assets" placeholder="Search by tag, name, serial number or model" value={filters.search} onChange={set('search')} /></div>
            <div className="col-6 col-lg-3">
              <select className="form-select" aria-label="Status" value={filters.status} onChange={set('status')}>
                <option value="">All statuses</option>
                {Object.entries(ASSET_STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div className="col-6 col-lg-3">
              <select className="form-select" aria-label="Category" value={filters.category} onChange={set('category')}>
                <option value="">All categories</option>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          </div>
        )}
        <ErrorAlert message={error} onRetry={load} />
        {loading ? <Loading /> : data.results.length === 0 ? (
          <EmptyState title={hasFilters ? 'No assets match your filters' : isStaff ? 'No assets yet' : 'No equipment is assigned to you'}>
            {isAdmin && !hasFilters ? 'Add your first asset to start tracking inventory.' : ''}
          </EmptyState>
        ) : (
          <div className="table-responsive">
            <table className="table align-middle">
              <thead><tr><th>Asset tag</th><th>Name</th><th>Category</th><th>Status</th>{isStaff && <th>Assigned to</th>}<th>Warranty until</th></tr></thead>
              <tbody>
                {data.results.map((a) => (
                  <tr key={a.id}>
                    <td><Link to={`/assets/${a.id}`}>{a.asset_tag}</Link></td>
                    <td>{a.name || [a.manufacturer, a.model_name].filter(Boolean).join(' ') || '—'}</td>
                    <td>{a.category_name}</td>
                    <td><AssetStatusBadge status={a.status} /></td>
                    {isStaff && <td>{a.assigned_to_name || '—'}</td>}
                    <td>{formatDate(a.warranty_expiry)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pagination page={page} count={data.count} onChange={setPage} />
      </div>
    </>
  );
}
