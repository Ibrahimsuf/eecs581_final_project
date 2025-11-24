async function markApplied(jobId, notes) {
  const res = await fetch(`/api/jobs/${jobId}/apply`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': window.CURRENT_USER_ID || ''
    },
    body: JSON.stringify({ notes })
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }
  return res.json();
}
async function unmarkApplied(jobId) {
  const res = await fetch(`/api/jobs/${jobId}/apply`, {
    method: 'DELETE',
    headers: {
      'X-User-Id': window.CURRENT_USER_ID || ''
    }
  });
  if (res.status === 204) {
    return { success: true };
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }
  return res.json();
}
