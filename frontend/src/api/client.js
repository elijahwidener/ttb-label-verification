// API base resolution:
// - On elijahwf.com the app is served through a Vercel rewrite of /ttb/*, so
//   API calls must also go through /ttb/api/* (Vercel proxies that to the
//   SWA's /api/*; see vercel.json at the repo root).
// - On the azurestaticapps.net host (and local dev) the API is at /api.
const onVercelProxy = window.location.hostname.endsWith('elijahwf.com')
export const API_BASE = onVercelProxy ? '/ttb/api' : '/api'

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  let body = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON error body */
  }
  if (!res.ok) {
    const err = new Error(body?.notification?.message || body?.error || `Request failed (${res.status})`)
    err.status = res.status
    err.body = body
    throw err
  }
  return body
}

export function getUploadUrl(filename, contentType, side) {
  return request('/upload-url', {
    method: 'POST',
    body: JSON.stringify({ filename, content_type: contentType, side }),
  })
}

// Direct PUT to Azure Blob Storage with the short-lived write SAS.
export async function uploadToBlob(uploadUrl, file) {
  const res = await fetch(uploadUrl, {
    method: 'PUT',
    headers: {
      'x-ms-blob-type': 'BlockBlob',
      'Content-Type': file.type,
    },
    body: file,
  })
  if (!res.ok) throw new Error(`Image upload failed (${res.status})`)
}

export function submitApplication(payload) {
  return request('/submit', { method: 'POST', body: JSON.stringify(payload) })
}

export function createBatch(total, submitterNote) {
  return request('/batches', {
    method: 'POST',
    body: JSON.stringify({ total, submitter_note: submitterNote || null }),
  })
}

export function getBatch(batchId) {
  return request(`/batches/${batchId}`)
}

export function listApplications(params = {}) {
  const qs = new URLSearchParams(params).toString()
  return request(`/applications${qs ? `?${qs}` : ''}`)
}

export function getApplication(id) {
  return request(`/applications/${id}`)
}

export function overrideApplication(id, explanation) {
  return request(`/applications/${id}/override`, {
    method: 'POST',
    body: JSON.stringify({ attestation: true, explanation }),
  })
}

export function decideApplication(id, decision, comment) {
  return request(`/applications/${id}/decide`, {
    method: 'POST',
    body: JSON.stringify({ decision, comment: comment || null }),
  })
}

// Submit error responses (400 image_unusable) come back as thrown errors with
// err.body populated — helper to recognize them.
export function isImageUnusable(err) {
  return err?.status === 400 && err?.body?.error === 'image_unusable'
}
