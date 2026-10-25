export const STATUS_LABELS = {
  NEW: 'New', ASSIGNED: 'Assigned', IN_PROGRESS: 'In progress', PENDING: 'Pending',
  RESOLVED: 'Resolved', CLOSED: 'Closed', REOPENED: 'Reopened',
};
export const PRIORITY_LABELS = { LOW: 'Low', MEDIUM: 'Medium', HIGH: 'High', CRITICAL: 'Critical' };
export const ROLE_LABELS = { ADMIN: 'Administrator', AGENT: 'IT Support Agent', EMPLOYEE: 'Employee' };
export const ASSET_STATUS_LABELS = {
  AVAILABLE: 'Available', ASSIGNED: 'Assigned', MAINTENANCE: 'Under maintenance',
  RETIRED: 'Retired', DAMAGED: 'Damaged', LOST: 'Lost',
};
export const STATUS_COLORS = {
  NEW: '#3b82f6', ASSIGNED: '#6366f1', IN_PROGRESS: '#0f766e', PENDING: '#d97706',
  RESOLVED: '#16a34a', CLOSED: '#64748b', REOPENED: '#dc2626',
};
export const PRIORITY_COLORS = { LOW: '#16a34a', MEDIUM: '#ca8a04', HIGH: '#ea580c', CRITICAL: '#dc2626' };
export const ASSET_COLORS = {
  AVAILABLE: '#16a34a', ASSIGNED: '#3b82f6', MAINTENANCE: '#d97706', RETIRED: '#64748b', DAMAGED: '#dc2626', LOST: '#7c3aed',
};

export const label = (map, key) => map[key] || key || '—';

export function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}
export function formatDateTime(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

/** Paginated endpoints return {results: [...]}; reference endpoints return a plain array. */
export const unwrap = (response) => response.data?.results ?? response.data;

const prettyField = (key) => key.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());

/** Turns any Axios error into one readable sentence, keeping the backend's own message when there is one. */
export function errorMessage(err, fallback = 'Something went wrong. Please try again.') {
  if (!err?.response) return 'Cannot reach the server. Check your connection and that the backend is running.';
  const { status, data } = err.response;
  if (data && typeof data === 'object') {
    if (typeof data.detail === 'string') return data.detail;
    const parts = Object.entries(data).map(([key, value]) => {
      const text = Array.isArray(value) ? value.join(' ') : typeof value === 'string' ? value : JSON.stringify(value);
      return key === 'non_field_errors' ? text : `${prettyField(key)}: ${text}`;
    });
    if (parts.length) return parts.join(' ');
  }
  if (status === 403) return 'You do not have permission to do that.';
  if (status === 404) return 'That item could not be found.';
  if (status >= 500) return 'The server had a problem. Please try again in a moment.';
  return fallback;
}
