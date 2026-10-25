import { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { EmptyState, ErrorAlert, Loading, PriorityBadge, StatusBadge, SuccessAlert } from '../components/ui';
import { PRIORITY_LABELS, STATUS_LABELS, errorMessage, formatDateTime, label, unwrap } from '../utils';

const CONFIRM = {
  RESOLVED: 'Mark this ticket as resolved?',
  CLOSED: 'Close this ticket? You will need to reopen it if the problem comes back.',
  REOPENED: 'Reopen this ticket?',
};

export default function TicketDetail() {
  const { id } = useParams();
  const location = useLocation();
  const { user, isStaff, isAdmin, isAgent } = useAuth();

  const [ticket, setTicket] = useState(null);
  const [comments, setComments] = useState([]);
  const [history, setHistory] = useState([]);
  const [agents, setAgents] = useState([]);
  const [assets, setAssets] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(location.state?.created ? `Ticket ${location.state.created} was created. IT support has been notified.` : '');
  const [busy, setBusy] = useState('');

  const [nextStatus, setNextStatus] = useState('');
  const [reason, setReason] = useState('');
  const [notes, setNotes] = useState('');
  const [agentId, setAgentId] = useState('');
  const [priority, setPriority] = useState('');
  const [assetId, setAssetId] = useState('');
  const [comment, setComment] = useState('');
  const [internal, setInternal] = useState(false);

  async function load() {
    try {
      const [t, c, h] = await Promise.all([api.get(`/tickets/${id}/`), api.get(`/tickets/${id}/comments/`), api.get(`/tickets/${id}/history/`)]);
      setTicket(t.data); setComments(c.data); setHistory(h.data);
      setPriority(t.data.priority); setAssetId(t.data.asset ? String(t.data.asset) : '');
      setError('');
    } catch (e) {
      setError(errorMessage(e, 'Unable to load this ticket.'));
    }
  }
  useEffect(() => { load(); }, [id]);

  useEffect(() => {
    if (!ticket || !isStaff) return;
    api.get('/users/assignable/?scope=agents').then((r) => setAgents(r.data)).catch(() => {});
    api.get('/assets/', { params: { assigned_to: ticket.created_by, page_size: 100 } }).then((r) => setAssets(unwrap(r))).catch(() => {});
  }, [ticket?.id, ticket?.created_by, isStaff]);

  /** Runs one API action with a busy flag, shows the backend's own error message, then refreshes. */
  async function run(name, action, success) {
    setBusy(name); setError(''); setNotice('');
    try {
      await action();
      if (success) setNotice(success);
      await load();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy('');
    }
  }

  function changeStatus(e) {
    e.preventDefault();
    if (CONFIRM[nextStatus] && !window.confirm(CONFIRM[nextStatus])) return;
    run('status', async () => {
      await api.post(`/tickets/${id}/status/`, { status: nextStatus, reason, resolution_notes: notes });
      setNextStatus(''); setReason(''); setNotes('');
    }, 'Status updated.');
  }

  const assign = (agent) => run('assign', () => api.post(`/tickets/${id}/assign/`, { agent_id: agent }), 'Assignment saved.');
  const saveDetails = () => run('edit', () => api.patch(`/tickets/${id}/`, { priority, asset: assetId ? Number(assetId) : null }), 'Ticket updated.');
  const addComment = (e) => {
    e.preventDefault();
    run('comment', async () => { await api.post(`/tickets/${id}/comments/`, { comment, is_internal: internal }); setComment(''); setInternal(false); }, 'Comment added.');
  };

  if (!ticket) return error ? <ErrorAlert message={error} onRetry={load} /> : <Loading />;

  const transitions = ticket.allowed_transitions;
  const needsReason = nextStatus === 'PENDING' || nextStatus === 'REOPENED';
  const needsNotes = nextStatus === 'RESOLVED';
  const iAmAgent = ticket.assigned_agent === user.id;

  function noActionsText() {
    if (!isStaff) {
      return ticket.status === 'CLOSED' ? '' : 'IT support is handling this ticket. You can close or reopen it once it is resolved.';
    }
    if (ticket.status === 'NEW' || (ticket.status === 'REOPENED' && !ticket.assigned_agent)) return 'Assign this ticket to an agent to start working on it.';
    if (isAgent && !iAmAgent) return 'Only the assigned agent can change this ticket\'s status.';
    return 'No further status changes are available.';
  }

  return (
    <>
      <Link to="/tickets">← Back to tickets</Link>
      <div className="page-header mt-3">
        <div>
          <h1>{ticket.ticket_number}</h1>
          <p className="text-muted mb-0">{ticket.title}</p>
        </div>
        <div className="d-flex gap-2 align-items-center"><PriorityBadge priority={ticket.priority} /><StatusBadge status={ticket.status} /></div>
      </div>

      <SuccessAlert message={notice} onClose={() => setNotice('')} />
      <ErrorAlert message={error} />

      <div className="row g-3">
        <div className="col-lg-8">
          <div className="panel mb-3">
            <h2>Description</h2>
            <p className="preserve-lines">{ticket.description}</p>
            <hr />
            <dl className="kv mb-0">
              <dt>Created by</dt><dd>{ticket.created_by_name || 'Unknown user'}</dd>
              <dt>Department</dt><dd>{ticket.department_name || '—'}</dd>
              <dt>Category</dt><dd>{ticket.category_name}</dd>
              <dt>Assigned agent</dt><dd>{ticket.assigned_agent_name || 'Unassigned'}</dd>
              <dt>Related asset</dt>
              <dd>{ticket.asset ? <Link to={`/assets/${ticket.asset}`}>{ticket.asset_tag} · {ticket.asset_name}</Link> : 'None'}</dd>
              <dt>Created</dt><dd>{formatDateTime(ticket.created_at)}</dd>
              <dt>Last updated</dt><dd>{formatDateTime(ticket.updated_at)}</dd>
              {ticket.resolved_at && <><dt>Resolved</dt><dd>{formatDateTime(ticket.resolved_at)}</dd></>}
            </dl>
            {ticket.resolution_notes && (
              <div className="alert alert-success mt-3 mb-0"><b>Resolution:</b> <span className="preserve-lines">{ticket.resolution_notes}</span></div>
            )}
          </div>

          <div className="panel">
            <h2>Comments</h2>
            {comments.length === 0 && <p className="text-muted">No comments yet.</p>}
            {comments.map((c) => (
              <div key={c.id} className={`comment-item ${c.is_internal ? 'internal' : ''}`}>
                <b>{c.author_name || 'Unknown user'}</b>
                {c.is_internal && <span className="pill priority-MEDIUM ms-2">Internal note</span>}
                <small className="text-muted ms-2">{formatDateTime(c.created_at)}</small>
                <p className="mb-0 mt-1 preserve-lines">{c.comment}</p>
              </div>
            ))}
            {ticket.status === 'CLOSED' ? (
              <p className="text-muted mt-3 mb-0">This ticket is closed. Reopen it to add comments.</p>
            ) : (
              <form onSubmit={addComment} className="mt-3">
                <textarea className="form-control mb-2" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Write a comment" aria-label="Comment" required />
                {isStaff && (
                  <div className="form-check mb-2">
                    <input id="internal" type="checkbox" className="form-check-input" checked={internal} onChange={(e) => setInternal(e.target.checked)} />
                    <label htmlFor="internal" className="form-check-label">Internal note (the requester will not see it)</label>
                  </div>
                )}
                <button className="btn btn-primary btn-sm" disabled={busy === 'comment'}>{busy === 'comment' ? 'Adding…' : 'Add comment'}</button>
              </form>
            )}
          </div>
        </div>

        <div className="col-lg-4">
          <div className="panel mb-3">
            <h2>Update status</h2>
            {transitions.length === 0 ? (
              <p className="text-muted mb-0">{noActionsText()}</p>
            ) : (
              <form onSubmit={changeStatus}>
                <select className="form-select mb-2" aria-label="Next status" value={nextStatus} onChange={(e) => setNextStatus(e.target.value)} required>
                  <option value="">Choose next status</option>
                  {transitions.map((s) => <option key={s} value={s}>{label(STATUS_LABELS, s)}</option>)}
                </select>
                {needsReason && <textarea className="form-control mb-2" rows={2} required value={reason} onChange={(e) => setReason(e.target.value)} placeholder={nextStatus === 'PENDING' ? 'Why is this on hold? (required)' : 'Why are you reopening it? (required)'} />}
                {needsNotes && <textarea className="form-control mb-2" rows={3} required value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="What was done to fix it? (required)" />}
                <button className="btn btn-primary btn-sm" disabled={!nextStatus || busy === 'status'}>{busy === 'status' ? 'Saving…' : 'Update status'}</button>
              </form>
            )}
          </div>

          {isStaff && ticket.can_assign && (
            <div className="panel mb-3">
              <h2>Assignment</h2>
              {isAgent && !ticket.assigned_agent ? (
                <button className="btn btn-primary btn-sm" disabled={busy === 'assign'} onClick={() => assign(user.id)}>Assign to me</button>
              ) : (
                <>
                  <select className="form-select mb-2" aria-label="Agent" value={agentId} onChange={(e) => setAgentId(e.target.value)}>
                    <option value="">{ticket.assigned_agent ? 'Reassign to…' : 'Choose an agent'}</option>
                    {agents.filter((a) => a.id !== ticket.assigned_agent).map((a) => <option key={a.id} value={a.id}>{a.full_name}</option>)}
                  </select>
                  <button className="btn btn-primary btn-sm" disabled={!agentId || busy === 'assign'} onClick={() => assign(Number(agentId))}>{ticket.assigned_agent ? 'Reassign' : 'Assign'}</button>
                </>
              )}
            </div>
          )}

          {isStaff && ticket.can_edit && (
            <div className="panel mb-3">
              <h2>Priority and asset</h2>
              <label className="form-label small" htmlFor="prio">Priority</label>
              <select id="prio" className="form-select mb-2" value={priority} onChange={(e) => setPriority(e.target.value)}>
                {Object.entries(PRIORITY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              <label className="form-label small" htmlFor="asset">Related asset (assigned to the requester)</label>
              <select id="asset" className="form-select mb-2" value={assetId} onChange={(e) => setAssetId(e.target.value)}>
                <option value="">None</option>
                {ticket.asset && !assets.some((a) => a.id === ticket.asset) && <option value={ticket.asset}>{ticket.asset_tag} · {ticket.asset_name}</option>}
                {assets.map((a) => <option key={a.id} value={a.id}>{a.asset_tag} · {a.name || [a.manufacturer, a.model_name].join(' ')}</option>)}
              </select>
              <button className="btn btn-outline-primary btn-sm" disabled={busy === 'edit'} onClick={saveDetails}>Save changes</button>
            </div>
          )}

          <div className="panel">
            <h2>History</h2>
            {history.length === 0 ? <EmptyState title="No history yet" /> : history.map((h) => (
              <div className="timeline-item" key={h.id}>
                <small className="text-muted">{formatDateTime(h.created_at)}</small>
                <div><b>{h.action}</b> <span className="text-muted">by {h.actor_name || 'Unknown user'}</span></div>
                {h.details && <small>{h.details}</small>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
