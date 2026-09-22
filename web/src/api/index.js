/**
 * One switch between fixtures and the real backend: VITE_USE_MOCKS.
 */

import { httpClient } from './httpClient.js'
import { mockClient, currentScenario } from './mockClient.js'

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true'
export const MOCK_SCENARIO = USE_MOCKS ? currentScenario() : null

export const api = USE_MOCKS ? mockClient : httpClient

export { ApiError, uiMessage, isAuthError, canRetry, GMAIL_DRAFTS_URL } from './errors.js'
export { SCENARIOS } from './mockClient.js'
