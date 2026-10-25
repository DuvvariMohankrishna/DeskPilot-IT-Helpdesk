import { useEffect, useState } from 'react';
import api from '../api';
import { EmptyState, ErrorAlert, Loading, PageHeader, SuccessAlert } from '../components/ui';
import { errorMessage } from '../utils';

const TABS = [
  { key: 'departments', title: 'Departments', endpoint: '/departments/', hasActive: true, hasDescription: true },
  { key: 'ticket', title: 'Ticket categories', endpoint: '/ticket-categories/', hasActive: true },
  { key: 'asset', title: 'Asset categories', endpoint: '/asset-categories/', hasActive: true },
];

function Manager({ tab }) {
  const [items, setItems] = useState(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [editId, setEditId] = useState(null);
  const [editName, setEditName] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  function load() { api.get(tab.endpoint).then((r) => setItems(r.data)).catch((e) => setError(errorMessage(e))); }
  useEffect(() => { setItems(null); setError(''); setNotice(''); setEditId(null); load(); }, [tab.key]);

  async function call(request, success) {
    setError(''); setNotice('');
    try { await request(); setNotice(success); load(); return true; } catch (e) { setError(errorMessage(e)); return false; }
  }

  async function add(e) {
    e.preventDefault();
    const body = { name: name.trim() };
    if (tab.hasDescription) body.description = description;
    if (await call(() => api.post(tab.endpoint, body), 'Added.')) { setName(''); setDescription(''); }
  }

  const rename = async (item) => { if (await call(() => api.patch(`${tab.endpoint}${item.id}/`, { name: editName.trim() }), 'Saved.')) setEditId(null); };
  const toggle = (item) => call(() => api.patch(`${tab.endpoint}${item.id}/`, { is_active: !item.is_active }), item.is_active ? 'Deactivated. It stays on existing records but cannot be chosen for new ones.' : 'Activated.');

  return (
    <div className="panel">
      <ErrorAlert message={error} />
      <SuccessAlert message={notice} onClose={() => setNotice('')} />
      <form className="row g-2 mb-3" onSubmit={add}>
        <div className="col-md-4"><input className="form-control" required placeholder="Name" aria-label="Name" value={name} onChange={(e) => setName(e.target.value)} /></div>
        {tab.hasDescription && <div className="col-md-5"><input className="form-control" placeholder="Description (optional)" aria-label="Description" value={description} onChange={(e) => setDescription(e.target.value)} /></div>}
        <div className="col-auto"><button className="btn btn-primary">Add</button></div>
      </form>
      {!items ? <Loading /> : items.length === 0 ? <EmptyState title={`No ${tab.title.toLowerCase()} yet`}>Add one above.</EmptyState> : (
        <table className="table align-middle">
          <thead><tr><th>Name</th>{tab.hasDescription && <th>Description</th>}{tab.hasActive && <th>Status</th>}<th /></tr></thead>
          <tbody>{items.map((item) => (
            <tr key={item.id}>
              <td>{editId === item.id ? <input className="form-control form-control-sm" value={editName} onChange={(e) => setEditName(e.target.value)} /> : item.name}</td>
              {tab.hasDescription && <td className="text-muted">{item.description || '—'}</td>}
              {tab.hasActive && <td>{item.is_active ? <span className="pill asset-AVAILABLE">Active</span> : <span className="pill asset-RETIRED">Inactive</span>}</td>}
              <td className="text-end text-nowrap">
                {editId === item.id ? (
                  <><button className="btn btn-sm btn-primary me-1" onClick={() => rename(item)}>Save</button><button className="btn btn-sm btn-light" onClick={() => setEditId(null)}>Cancel</button></>
                ) : (
                  <><button className="btn btn-sm btn-outline-primary me-1" onClick={() => { setEditId(item.id); setEditName(item.name); }}>Rename</button>
                    {tab.hasActive && <button className="btn btn-sm btn-outline-secondary" onClick={() => toggle(item)}>{item.is_active ? 'Deactivate' : 'Activate'}</button>}</>
                )}
              </td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}

export default function Settings() {
  const [active, setActive] = useState('departments');
  const tab = TABS.find((t) => t.key === active);
  return (
    <>
      <PageHeader title="Departments & categories" subtitle="Reference data used by tickets, users and assets. Items are deactivated, never deleted, so history stays intact." />
      <ul className="nav nav-tabs mb-3">
        {TABS.map((t) => <li className="nav-item" key={t.key}><button className={`nav-link ${active === t.key ? 'active' : ''}`} onClick={() => setActive(t.key)}>{t.title}</button></li>)}
      </ul>
      <Manager tab={tab} />
    </>
  );
}
