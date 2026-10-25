import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { EmptyState, ErrorAlert, Loading, PageHeader, Pagination, TicketTable } from '../components/ui';
import { PRIORITY_LABELS, STATUS_LABELS, errorMessage, unwrap } from '../utils';

const SORTS = {
  newest: { label: 'Newest first', ordering: '-created_at' },
  oldest: { label: 'Oldest first', ordering: 'created_at' },
  updated: { label: 'Recently updated', ordering: '-updated_at' },
  priority: { label: 'Highest priority first', ordering: '-priority_rank' },
};

export default function Tickets() {
  const { isStaff } = useAuth();
  const [params] = useSearchParams();
  const [filters, setFilters] = useState({
    search: '', status: params.get('status') || '', priority: '', category: '', department: '',
    agent: params.get('unassigned') === 'true' ? 'none' : '', sort: 'newest',
  });
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [agents, setAgents] = useState([]);
  const [data, setData] = useState({ count: 0, results: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/ticket-categories/').then((r) => setCategories(r.data)).catch(() => {});
    if (isStaff) {
      api.get('/departments/').then((r) => setDepartments(r.data)).catch(() => {});
      api.get('/users/assignable/?scope=agents').then((r) => setAgents(r.data)).catch(() => {});
    }
  }, [isStaff]);

  function load() {
    setLoading(true);
    setError('');
    const query = {
      page, ordering: SORTS[filters.sort].ordering,
      search: filters.search || undefined, status: filters.status || undefined, priority: filters.priority || undefined,
      category: filters.category || undefined, department: filters.department || undefined,
    };
    if (filters.agent === 'none') query.unassigned = true;
    else if (filters.agent) query.assigned_agent = filters.agent;
    api.get('/tickets/', { params: query })
      .then((r) => setData(r.data))
      .catch((e) => setError(errorMessage(e, 'Unable to load tickets.')))
      .finally(() => setLoading(false));
  }

  // search is debounced so we do not call the API on every keystroke
  useEffect(() => {
    const timer = setTimeout(load, filters.search ? 350 : 0);
    return () => clearTimeout(timer);
  }, [filters, page]);

  const set = (key) => (e) => { setFilters({ ...filters, [key]: e.target.value }); setPage(1); };
  const hasFilters = filters.search || filters.status || filters.priority || filters.category || filters.department || filters.agent;

  return (
    <>
      <PageHeader title={isStaff ? 'Tickets' : 'My tickets'} subtitle="Search, filter and track support requests.">
        <Link className="btn btn-primary" to="/tickets/new">Create ticket</Link>
      </PageHeader>
      <div className="panel">
        <div className="row g-2 mb-3">
          <div className="col-lg-4"><input className="form-control" placeholder="Search by ticket number or title" aria-label="Search tickets" value={filters.search} onChange={set('search')} /></div>
          <div className="col-6 col-lg-2">
            <select className="form-select" aria-label="Status" value={filters.status} onChange={set('status')}>
              <option value="">All statuses</option>
              {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div className="col-6 col-lg-2">
            <select className="form-select" aria-label="Priority" value={filters.priority} onChange={set('priority')}>
              <option value="">All priorities</option>
              {Object.entries(PRIORITY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div className="col-6 col-lg-2">
            <select className="form-select" aria-label="Category" value={filters.category} onChange={set('category')}>
              <option value="">All categories</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className="col-6 col-lg-2">
            <select className="form-select" aria-label="Sort" value={filters.sort} onChange={set('sort')}>
              {Object.entries(SORTS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
          </div>
          {isStaff && <>
            <div className="col-6 col-lg-3">
              <select className="form-select" aria-label="Department" value={filters.department} onChange={set('department')}>
                <option value="">All departments</option>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <div className="col-6 col-lg-3">
              <select className="form-select" aria-label="Assigned agent" value={filters.agent} onChange={set('agent')}>
                <option value="">Any assignment</option>
                <option value="none">Unassigned</option>
                {agents.map((a) => <option key={a.id} value={a.id}>{a.full_name}</option>)}
              </select>
            </div>
          </>}
        </div>

        <ErrorAlert message={error} onRetry={load} />
        {loading ? <Loading /> : data.results.length === 0 ? (
          <EmptyState title={hasFilters ? 'No tickets match your filters' : 'No tickets yet'}
            action={hasFilters
              ? <button className="btn btn-sm btn-outline-secondary" onClick={() => { setFilters({ ...filters, search: '', status: '', priority: '', category: '', department: '', agent: '' }); setPage(1); }}>Clear filters</button>
              : <Link className="btn btn-primary btn-sm" to="/tickets/new">Create ticket</Link>}>
            {hasFilters ? 'Try removing a filter.' : 'Create a ticket when you need help from IT.'}
          </EmptyState>
        ) : <TicketTable items={data.results} showAgent={isStaff} />}
        <Pagination page={page} count={data.count} onChange={setPage} />
      </div>
    </>
  );
}
