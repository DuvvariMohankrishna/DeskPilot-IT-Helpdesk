import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { EmptyState, ErrorAlert, Loading, PageHeader, StatCard, TicketTable, AssetStatusBadge } from '../components/ui';
import {
  ASSET_COLORS, ASSET_STATUS_LABELS, PRIORITY_COLORS, PRIORITY_LABELS, STATUS_COLORS, STATUS_LABELS,
  errorMessage, formatDateTime, label,
} from '../utils';

function ChartCard({ title, data, kind = 'bar' }) {
  return (
    <div className="panel h-100">
      <h2>{title}</h2>
      {data.length === 0 ? (
        <EmptyState title="No data yet">Charts appear once there are records to show.</EmptyState>
      ) : (
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            {kind === 'pie' ? (
              <PieChart>
                <Pie data={data} dataKey="count" nameKey="name" outerRadius={85} label>
                  {data.map((d) => <Cell key={d.name} fill={d.color} />)}
                </Pie>
                <Tooltip /><Legend />
              </PieChart>
            ) : (
              <BarChart data={data}>
                <XAxis dataKey="name" interval={0} tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {data.map((d) => <Cell key={d.name} fill={d.color} />)}
                </Bar>
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

const statusData = (rows = []) => rows.map((r) => ({ name: label(STATUS_LABELS, r.status), count: r.count, color: STATUS_COLORS[r.status] }));
const priorityData = (rows = []) => rows.map((r) => ({ name: label(PRIORITY_LABELS, r.priority), count: r.count, color: PRIORITY_COLORS[r.priority] }));
const categoryData = (rows = []) => rows.map((r) => ({ name: r.category, count: r.count, color: '#0f766e' }));
const assetData = (rows = []) => rows.map((r) => ({ name: label(ASSET_STATUS_LABELS, r.status), count: r.count, color: ASSET_COLORS[r.status] }));

export default function Dashboard() {
  const { user, isAdmin, isAgent } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const path = isAdmin ? 'admin' : isAgent ? 'agent' : 'employee';

  function load() {
    setError('');
    api.get(`/dashboard/${path}/`).then((r) => setData(r.data)).catch((e) => setError(errorMessage(e)));
  }
  useEffect(load, [path]);

  if (error) return <ErrorAlert message={error} onRetry={load} />;
  if (!data) return <Loading />;

  const subtitle = isAdmin ? 'Overview of all tickets and assets.' : isAgent ? 'Your workload and the queue waiting for an agent.' : 'Your support requests and equipment.';

  return (
    <>
      <PageHeader title={`Welcome, ${user.first_name || user.username}`} subtitle={subtitle}>
        <Link className="btn btn-primary" to="/tickets/new">Create ticket</Link>
      </PageHeader>

      <div className="row g-3 mb-4">
        {isAdmin && <>
          <div className="col-6 col-lg-3"><StatCard label="Total tickets" value={data.total_tickets} to="/tickets" /></div>
          <div className="col-6 col-lg-3"><StatCard label="New and unassigned" value={data.unassigned_tickets} tone="warn" to="/tickets?unassigned=true" /></div>
          <div className="col-6 col-lg-3"><StatCard label="In progress" value={data.in_progress_tickets} tone="info" to="/tickets?status=IN_PROGRESS" /></div>
          <div className="col-6 col-lg-3"><StatCard label="Pending" value={data.pending_tickets} tone="warn" to="/tickets?status=PENDING" /></div>
          <div className="col-6 col-lg-3"><StatCard label="Resolved" value={data.resolved_tickets} tone="good" to="/tickets?status=RESOLVED" /></div>
          <div className="col-6 col-lg-3"><StatCard label="Closed" value={data.closed_tickets} to="/tickets?status=CLOSED" /></div>
          <div className="col-6 col-lg-3"><StatCard label="Assets available / assigned" value={`${data.available_assets} / ${data.assigned_assets}`} to="/assets" /></div>
          <div className="col-6 col-lg-3"><StatCard label="Assets under maintenance" value={data.maintenance_assets} tone="warn" to="/assets?status=MAINTENANCE" /></div>
        </>}
        {isAgent && <>
          <div className="col-6 col-lg"><StatCard label="Assigned to me (open)" value={data.open_tickets} to="/tickets" /></div>
          <div className="col-6 col-lg"><StatCard label="Needs attention" value={data.needs_attention} tone="danger" /></div>
          <div className="col-6 col-lg"><StatCard label="In progress" value={data.in_progress_tickets} tone="info" /></div>
          <div className="col-6 col-lg"><StatCard label="Pending" value={data.pending_tickets} tone="warn" /></div>
          <div className="col-6 col-lg"><StatCard label="Waiting for an agent" value={data.eligible_unassigned} tone="warn" to="/tickets?unassigned=true" /></div>
        </>}
        {!isAdmin && !isAgent && <>
          <div className="col-6 col-lg"><StatCard label="My tickets" value={data.total_tickets} to="/tickets" /></div>
          <div className="col-6 col-lg"><StatCard label="Open" value={data.open_tickets} tone="info" /></div>
          <div className="col-6 col-lg"><StatCard label="Pending" value={data.pending_tickets} tone="warn" /></div>
          <div className="col-6 col-lg"><StatCard label="Resolved" value={data.resolved_tickets} tone="good" /></div>
          <div className="col-6 col-lg"><StatCard label="My assets" value={data.total_assets} to="/assets" /></div>
        </>}
      </div>

      <div className="row g-3 mb-4">
        <div className="col-lg-6"><ChartCard title="Tickets by status" data={statusData(data.tickets_by_status)} /></div>
        <div className="col-lg-6"><ChartCard title="Tickets by priority" kind="pie" data={priorityData(data.tickets_by_priority)} /></div>
        {(isAdmin || isAgent) && <div className="col-lg-6"><ChartCard title="Tickets by category" data={categoryData(data.tickets_by_category)} /></div>}
        {isAdmin && <div className="col-lg-6"><ChartCard title="Asset inventory by status" kind="pie" data={assetData(data.assets_by_status)} /></div>}
      </div>

      {isAgent && (
        <div className="panel mb-4">
          <h2>Queue: tickets waiting for an agent</h2>
          {data.unassigned_queue.length ? <TicketTable items={data.unassigned_queue} showAgent={false} /> : <EmptyState title="The queue is empty">New tickets will show up here.</EmptyState>}
        </div>
      )}

      <div className="panel mb-4">
        <h2>{isAdmin ? 'Recently updated tickets' : isAgent ? 'My recently updated tickets' : 'My recent tickets'}</h2>
        {data.recent_tickets.length
          ? <TicketTable items={data.recent_tickets} />
          : <EmptyState title="No tickets yet" action={<Link className="btn btn-primary btn-sm" to="/tickets/new">Create ticket</Link>}>Tickets you create or handle appear here.</EmptyState>}
      </div>

      {isAgent && data.recently_resolved.length > 0 && (
        <div className="panel mb-4"><h2>Recently resolved</h2><TicketTable items={data.recently_resolved} /></div>
      )}

      {isAdmin && (
        <div className="panel">
          <h2>Recent activity</h2>
          {data.recent_activity.length === 0 ? <EmptyState title="No activity yet" /> : data.recent_activity.map((h) => (
            <div className="timeline-item" key={h.id}>
              <small className="text-muted">{formatDateTime(h.created_at)}</small>
              <div><b>{h.action}</b> by {h.actor_name} · <Link to={`/tickets/${h.ticket}`}>open ticket</Link></div>
              <small>{h.details}</small>
            </div>
          ))}
        </div>
      )}

      {!isAdmin && !isAgent && data.my_assets.length > 0 && (
        <div className="panel">
          <h2>My assets</h2>
          {data.my_assets.map((a) => (
            <div key={a.id} className="d-flex justify-content-between border-bottom py-2">
              <Link to={`/assets/${a.id}`}>{a.asset_tag} · {a.name || [a.manufacturer, a.model_name].join(' ')}</Link>
              <AssetStatusBadge status={a.status} />
            </div>
          ))}
        </div>
      )}
    </>
  );
}
