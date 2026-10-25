import { Link } from 'react-router-dom';
import { ASSET_STATUS_LABELS, PRIORITY_LABELS, STATUS_LABELS, label } from '../utils';

export function Loading({ text = 'Loading…' }) {
  return (
    <div className="state-box" role="status">
      <div className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
      {text}
    </div>
  );
}

export function ErrorAlert({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="alert alert-danger d-flex justify-content-between align-items-center" role="alert">
      <span>{message}</span>
      {onRetry && <button className="btn btn-sm btn-outline-danger ms-3" onClick={onRetry}>Try again</button>}
    </div>
  );
}

export function SuccessAlert({ message, onClose }) {
  if (!message) return null;
  return (
    <div className="alert alert-success d-flex justify-content-between align-items-center" role="status">
      <span>{message}</span>
      {onClose && <button className="btn-close" aria-label="Dismiss" onClick={onClose} />}
    </div>
  );
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="state-box flex-column text-center">
      <strong>{title}</strong>
      {children && <p className="text-muted mb-2 mt-1">{children}</p>}
      {action}
    </div>
  );
}

export const StatusBadge = ({ status }) => <span className={`pill status-${status}`}>{label(STATUS_LABELS, status)}</span>;
export const PriorityBadge = ({ priority }) => <span className={`pill priority-${priority}`}>{label(PRIORITY_LABELS, priority)}</span>;
export const AssetStatusBadge = ({ status }) => <span className={`pill asset-${status}`}>{label(ASSET_STATUS_LABELS, status)}</span>;

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="text-muted mb-0">{subtitle}</p>}
      </div>
      <div className="d-flex gap-2 flex-wrap">{children}</div>
    </div>
  );
}

export function StatCard({ label: text, value, to, tone }) {
  const body = (
    <div className={`stat-card ${tone ? `tone-${tone}` : ''}`}>
      <div className="stat-label">{text}</div>
      <div className="stat-number">{value ?? '—'}</div>
    </div>
  );
  return to ? <Link to={to} className="stat-link">{body}</Link> : body;
}

export function Pagination({ page, count, pageSize = 10, onChange }) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (count <= pageSize) return null;
  return (
    <nav className="d-flex justify-content-between align-items-center mt-3" aria-label="Pagination">
      <small className="text-muted">{count} records · page {page} of {pages}</small>
      <div className="btn-group">
        <button className="btn btn-sm btn-outline-secondary" disabled={page <= 1} onClick={() => onChange(page - 1)}>Previous</button>
        <button className="btn btn-sm btn-outline-secondary" disabled={page >= pages} onClick={() => onChange(page + 1)}>Next</button>
      </div>
    </nav>
  );
}

export function TicketTable({ items, showAgent = true }) {
  return (
    <div className="table-responsive">
      <table className="table align-middle">
        <thead>
          <tr>
            <th>Ticket</th><th>Title</th><th>Category</th><th>Priority</th><th>Status</th>
            {showAgent && <th>Assigned to</th>}<th>Created</th>
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr key={t.id}>
              <td><Link to={`/tickets/${t.id}`}>{t.ticket_number}</Link></td>
              <td className="cell-title">{t.title}</td>
              <td>{t.category_name}</td>
              <td><PriorityBadge priority={t.priority} /></td>
              <td><StatusBadge status={t.status} /></td>
              {showAgent && <td>{t.assigned_agent_name || <span className="text-muted">Unassigned</span>}</td>}
              <td>{new Date(t.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
