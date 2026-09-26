/**
 * Real client for Contract A.
 *
 * The session lives in the HttpOnly `draftagent_session` cookie, so every call
 * sends credentials. Google tokens and the OpenAI key never reach the browser.
 */

import { ApiError } from './errors.js'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      credentials: 'include',
      headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
      ...options,
    })
  } catch {
    throw new ApiError({ code: 'NETWORK', status: 0 })
  }

  if (response.status === 204) return null

  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    throw new ApiError({
      code: payload?.error?.code,
      status: response.status,
      message: payload?.error?.message,
    })
  }
  return payload
}

export const httpClient = {
  getMe: () => request('/auth/me'),

  // Full page redirect: the browser must follow the 302 to Google consent.
  startLogin: () => {
    window.location.href = `${BASE_URL}/auth/google/login`
  },

  logout: () => request('/auth/logout', { method: 'POST' }),

  listThreads: ({ pageToken, q } = {}) => {
    const params = new URLSearchParams()
    if (pageToken) params.set('page_token', pageToken)
    if (q) params.set('q', q)
    const query = params.toString()
    return request(`/threads${query ? `?${query}` : ''}`)
  },

  getThread: (id) => request(`/threads/${encodeURIComponent(id)}`),

  getStyleStatus: () => request('/style/status'),

  startRun: (gmailThreadId) =>
    request('/runs', { method: 'POST', body: JSON.stringify({ gmail_thread_id: gmailThreadId }) }),

  resumeRun: (runId, answer) =>
    request(`/runs/${encodeURIComponent(runId)}/resume`, {
      method: 'POST',
      body: JSON.stringify({ answer }),
    }),
}
