import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { EmptyState, ErrorAlert, Loading, PageHeader, Pagination } from '../components/ui';
import { errorMessage, formatDateTime } from '../utils';

export default function Notifications() {
  const nav = useNavigate();
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  function load() {
    api.get('/notifications/', { params: { page } }).then((r) => setData(r.data)).catch((e) => setError(errorMessage(e)));
  }
  useEffect(load, [page]);
  const changed = () => window.dispatchEvent(new Event('notifications:changed'));

  async function open(n) {
    try {
      if (!n.is_read) { await api.post(`/notifications/${n.id}/mark_read/`); changed(); }
      if (n.ticket) nav(`/tickets/${n.ticket}`);
      else if (n.asset) nav(`/assets/${n.asset}`);
      else load();
    } catch (e) { setError(errorMessage(e)); }
  }

  async function markAll() {
    try { await api.post('/notifications/mark_all_read/'); changed(); load(); } catch (e) { setError(errorMessage(e)); }
  }

  return (
    <>
      <PageHeader title="Notifications" subtitle="Updates about your tickets and equipment.">
        <button className="btn btn-outline-secondary" onClick={markAll}>Mark all as read</button>
      </PageHeader>
      <ErrorAlert message={error} />
      <div className="panel">
        {!data ? <Loading /> : data.results.length === 0 ? <EmptyState title="You are all caught up">New updates will appear here.</EmptyState> : data.results.map((n) => (
          <div key={n.id} className={`notification-item ${n.is_read ? '' : 'unread'}`}>
            <div>
              <div className={n.is_read ? '' : 'fw-semibold'}>{n.message}</div>
              <small className="text-muted">{formatDateTime(n.created_at)}</small>
            </div>
            {(n.ticket || n.asset) && <button className="btn btn-sm btn-outline-primary align-self-center" onClick={() => open(n)}>{n.ticket ? 'Open ticket' : 'Open asset'}</button>}
          </div>
        ))}
        {data && <Pagination page={page} count={data.count} onChange={setPage} />}
      </div>
    </>
  );
}
