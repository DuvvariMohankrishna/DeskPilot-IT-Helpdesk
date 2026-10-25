import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { AssetStatusBadge, ErrorAlert, Loading, PageHeader, SuccessAlert } from '../components/ui';
import { errorMessage, formatDate, formatDateTime } from '../utils';

const today = () => new Date().toISOString().slice(0, 10);

export default function AssetDetail() {
  const { id } = useParams();
  const { isAdmin, isStaff } = useAuth();
  const [asset, setAsset] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [maintenance, setMaintenance] = useState([]);
  const [history, setHistory] = useState([]);
  const [people, setPeople] = useState([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState('');
  const [employeeId, setEmployeeId] = useState('');
  const [reason, setReason] = useState('');
  const [service, setService] = useState({ maintenance_type: '', description: '', maintenance_date: today(), cost: '0', result: 'OPEN' });

  async function load() {
    try {
      const a = await api.get(`/assets/${id}/`);
      setAsset(a.data);
      if (isStaff) {
        const [h, m, events] = await Promise.all([api.get(`/assets/${id}/assignments/`), api.get(`/assets/${id}/maintenance/`), api.get(`/assets/${id}/history/`)]);
        setAssignments(h.data); setMaintenance(m.data); setHistory(events.data);
      }
      setError('');
    } catch (e) {
      setError(errorMessage(e, 'Unable to load this asset.'));
    }
  }
  useEffect(() => { load(); }, [id]);
  useEffect(() => { if (isAdmin) api.get('/users/assignable/?scope=employees').then((r) => setPeople(r.data)).catch(() => {}); }, [isAdmin]);

  async function run(name, action, success, confirmText) {
    if (confirmText && !window.confirm(confirmText)) return;
    setBusy(name); setError(''); setNotice('');
    try {
      await action();
      setNotice(success);
      setEmployeeId(''); setReason('');
      await load();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy('');
    }
  }

  if (!asset) return error ? <ErrorAlert message={error} onRetry={load} /> : <Loading />;

  const status = asset.status;
  const post = (path, body) => () => api.post(`/assets/${id}/${path}/`, body);
  const sv = (key) => (e) => setService({ ...service, [key]: e.target.value });

  return (
    <>
      <Link to="/assets">← Back to assets</Link>
      <PageHeader title={asset.asset_tag} subtitle={asset.name || [asset.manufacturer, asset.model_name].filter(Boolean).join(' ')}>
        <AssetStatusBadge status={status} />
        {isAdmin && status !== 'RETIRED' && <Link className="btn btn-outline-primary btn-sm" to={`/assets/${id}/edit`}>Edit</Link>}
      </PageHeader>
      <SuccessAlert message={notice} onClose={() => setNotice('')} />
      <ErrorAlert message={error} />

      <div className="row g-3">
        <div className="col-lg-7">
          <div className="panel mb-3">
            <h2>Details</h2>
            <dl className="kv mb-0">
              <dt>Category</dt><dd>{asset.category_name}</dd>
              <dt>Manufacturer / model</dt><dd>{[asset.manufacturer, asset.model_name].filter(Boolean).join(' ') || '—'}</dd>
              <dt>Serial number</dt><dd>{asset.serial_number || '—'}</dd>
              <dt>Assigned to</dt><dd>{asset.assigned_to_name || '—'}</dd>
              <dt>Department</dt><dd>{asset.department_name || '—'}</dd>
              <dt>Location</dt><dd>{asset.location || '—'}</dd>
              <dt>Purchased</dt><dd>{formatDate(asset.purchase_date)}</dd>
              <dt>Warranty until</dt><dd>{formatDate(asset.warranty_expiry)}</dd>
              {isStaff && <><dt>Purchase price</dt><dd>{asset.purchase_price ?? '—'}</dd><dt>Notes</dt><dd className="preserve-lines">{asset.notes || '—'}</dd></>}
            </dl>
          </div>

          {isStaff && (
            <>
              <div className="panel mb-3">
                <h2>Assignment history</h2>
                {assignments.length === 0 ? <p className="text-muted mb-0">This asset has never been assigned.</p> : (
                  <div className="table-responsive"><table className="table">
                    <thead><tr><th>Employee</th><th>Assigned</th><th>Returned</th><th>By</th><th>Reason</th></tr></thead>
                    <tbody>{assignments.map((a) => (
                      <tr key={a.id}><td>{a.employee_name}</td><td>{formatDateTime(a.assigned_at)}</td>
                        <td>{a.returned_at ? formatDateTime(a.returned_at) : <span className="pill asset-ASSIGNED">Current</span>}</td>
                        <td>{a.assigned_by_name}</td><td>{a.reason || '—'}</td></tr>
                    ))}</tbody>
                  </table></div>
                )}
              </div>
              <div className="panel">
                <h2>Maintenance history</h2>
                {maintenance.length === 0 ? <p className="text-muted mb-0">No maintenance has been recorded.</p> : (
                  <div className="table-responsive"><table className="table">
                    <thead><tr><th>Date</th><th>Type</th><th>Description</th><th>Cost</th><th>Result</th><th>Technician</th></tr></thead>
                    <tbody>{maintenance.map((m) => (
                      <tr key={m.id}><td>{formatDate(m.maintenance_date)}</td><td>{m.maintenance_type}</td><td>{m.description}</td><td>{m.cost}</td>
                        <td>{m.result === 'OPEN' ? <span className="pill asset-MAINTENANCE">Open</span> : <span className="pill asset-AVAILABLE">Completed</span>}</td>
                        <td>{m.technician_name}</td></tr>
                    ))}</tbody>
                  </table></div>
                )}
              </div>
              <div className="panel mt-3">
                <h2>Asset activity history</h2>
                {history.length === 0 ? <p className="text-muted mb-0">No activity has been recorded yet.</p> : (
                  <div className="table-responsive"><table className="table align-middle">
                    <thead><tr><th>When</th><th>Action</th><th>By</th><th>Details</th></tr></thead>
                    <tbody>{history.map((event) => <tr key={event.id}>
                      <td className="text-nowrap">{formatDateTime(event.created_at)}</td><td>{event.action}</td>
                      <td>{event.actor_name}</td><td className="preserve-lines">{event.details || '—'}</td>
                    </tr>)}</tbody>
                  </table></div>
                )}
              </div>
            </>
          )}
        </div>

        {isAdmin && (
          <div className="col-lg-5">
            {status === 'RETIRED' ? (
              <div className="panel"><h2>Retired</h2><p className="text-muted mb-0">This asset is retired. Its history is kept for records.</p></div>
            ) : (
              <>
                {(status === 'AVAILABLE' || status === 'ASSIGNED') && (
                  <div className="panel mb-3">
                    <h2>{status === 'ASSIGNED' ? 'Reassign or return' : 'Assign to a person'}</h2>
                    <select className="form-select mb-2" aria-label="Person" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
                      <option value="">Choose a person</option>
                      {people.filter((p) => p.id !== asset.assigned_to).map((p) => <option key={p.id} value={p.id}>{p.full_name}{p.department_name ? ` (${p.department_name})` : ''}</option>)}
                    </select>
                    <input className="form-control mb-2" placeholder="Reason (optional)" maxLength={250} value={reason} onChange={(e) => setReason(e.target.value)} />
                    <div className="d-flex gap-2 flex-wrap">
                      <button className="btn btn-primary btn-sm" disabled={!employeeId || busy === 'assign'}
                        onClick={() => run('assign', post(status === 'ASSIGNED' ? 'reassign' : 'assign', { employee_id: Number(employeeId), reason }), status === 'ASSIGNED' ? 'Asset reassigned.' : 'Asset assigned.')}>
                        {status === 'ASSIGNED' ? 'Reassign' : 'Assign'}
                      </button>
                      {status === 'ASSIGNED' && (
                        <button className="btn btn-outline-secondary btn-sm" disabled={busy === 'return'}
                          onClick={() => run('return', post('return'), 'Asset returned.', `Record the return of ${asset.asset_tag} from ${asset.assigned_to_name}?`)}>Record return</button>
                      )}
                    </div>
                  </div>
                )}

                {status === 'MAINTENANCE' && (
                  <div className="panel mb-3">
                    <h2>Under maintenance</h2>
                    <button className="btn btn-primary btn-sm" disabled={busy === 'complete'}
                      onClick={() => run('complete', post('complete-maintenance'), 'Maintenance completed. The asset is available again.')}>Complete maintenance</button>
                  </div>
                )}

                {status !== 'ASSIGNED' && (
                  <div className="panel mb-3">
                    <h2>Record maintenance</h2>
                    <form onSubmit={(e) => { e.preventDefault(); run('service', post('maintenance', service), 'Maintenance recorded.'); }}>
                      <input className="form-control mb-2" required placeholder="Type, e.g. Battery replacement" value={service.maintenance_type} onChange={sv('maintenance_type')} />
                      <textarea className="form-control mb-2" required rows={2} placeholder="What was done or is planned" value={service.description} onChange={sv('description')} />
                      <div className="row g-2 mb-2">
                        <div className="col-6"><input type="date" className="form-control" required aria-label="Date" value={service.maintenance_date} onChange={sv('maintenance_date')} /></div>
                        <div className="col-6"><input type="number" min="0" step="0.01" className="form-control" aria-label="Cost" placeholder="Cost" value={service.cost} onChange={sv('cost')} /></div>
                      </div>
                      <select className="form-select mb-2" aria-label="Result" value={service.result} onChange={sv('result')}>
                        <option value="OPEN">Open: take the asset out of service</option>
                        <option value="COMPLETED">Completed: add to history only</option>
                      </select>
                      <button className="btn btn-outline-primary btn-sm" disabled={busy === 'service'}>Save maintenance record</button>
                    </form>
                  </div>
                )}

                {status !== 'ASSIGNED' && (
                  <div className="panel mb-3">
                    <h2>Retire asset</h2>
                    <p className="text-muted small">Retired assets cannot be assigned or edited. History is kept.</p>
                    <button className="btn btn-outline-danger btn-sm" disabled={busy === 'retire'}
                      onClick={() => run('retire', post('retire'), 'Asset retired.', `Retire ${asset.asset_tag}? This cannot be undone.`)}>Retire asset</button>
                  </div>
                )}
                {status === 'AVAILABLE' && (
                  <div className="panel mb-3">
                    <h2>Report asset condition</h2>
                    <p className="text-muted small">Use these actions when an available asset is damaged or cannot be located.</p>
                    <div className="d-flex gap-2 flex-wrap">
                      <button className="btn btn-outline-warning btn-sm" disabled={!!busy} onClick={() => run('damaged', post('mark-damaged'), 'Asset marked as damaged.', `Mark ${asset.asset_tag} as damaged?`)}>Mark damaged</button>
                      <button className="btn btn-outline-danger btn-sm" disabled={!!busy} onClick={() => run('lost', post('mark-lost'), 'Asset marked as lost.', `Mark ${asset.asset_tag} as lost?`)}>Mark lost</button>
                    </div>
                  </div>
                )}
                {(status === 'DAMAGED' || status === 'LOST') && (
                  <div className="panel mb-3">
                    <h2>{status === 'LOST' ? 'Recover asset' : 'Repair / recover asset'}</h2>
                    <p className="text-muted small">Confirm that the asset has been recovered or is ready to return to service.</p>
                    <button className="btn btn-primary btn-sm" disabled={!!busy} onClick={() => run('recover', post('recover'), 'Asset returned to Available status.', `Mark ${asset.asset_tag} as recovered and available?`)}>Mark recovered / available</button>
                  </div>
                )}
                {status === 'ASSIGNED' && <p className="text-muted small">Return the asset before sending it to maintenance or retiring it.</p>}
              </>
            )}
          </div>
        )}
      </div>
    </>
  );
}
