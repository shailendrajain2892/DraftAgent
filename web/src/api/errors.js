/**
 * Error handling for Contract A.
 * Every failed call surfaces an ApiError, and the UI shows uiMessage() + Retry.
 */

export class ApiError extends Error {
  constructor({ code, status, message }) {
    super(message || code || 'Request failed')
    this.name = 'ApiError'
    this.code = code || 'UNKNOWN'
    this.status = status ?? 0
  }
}

/** UI copy per error code, from the Contract A table. */
const COPY = {
  UNAUTHENTICATED: 'Please connect your Gmail account.',
  AUTH_EXPIRED: 'Your session expired. Please connect Gmail again.',
  NOT_FOUND: 'We could not find that any more. Going back to your inbox.',
  RUN_STATE_CONFLICT: 'This draft run is no longer waiting for an answer. Start it again.',
  GMAIL_RATE_LIMITED: 'Gmail is busy. Try again in a moment.',
  UPSTREAM_ERROR: 'Gmail or the model did not respond. Try again.',
  RUN_TIMEOUT: 'That took too long. Try again.',
  NETWORK: 'Cannot reach the server. Check that the backend is running.',
  UNKNOWN: 'Something went wrong.',
}

export function uiMessage(error) {
  if (!error) return ''
  return COPY[error.code] || error.message || COPY.UNKNOWN
}

/** 401s send the user back to the Connect screen. */
export function isAuthError(error) {
  return error?.status === 401 || error?.code === 'UNAUTHENTICATED' || error?.code === 'AUTH_EXPIRED'
}

/** NOT_FOUND and RUN_STATE_CONFLICT are not worth retrying as-is. */
export function canRetry(error) {
  return !['NOT_FOUND', 'RUN_STATE_CONFLICT'].includes(error?.code)
}

export const GMAIL_DRAFTS_URL = 'https://mail.google.com/mail/u/0/#drafts'
