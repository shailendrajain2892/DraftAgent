/**
 * Mock client: serves the fixture JSON in web/mocks/ so the UI can be built and
 * demoed before the backend exists. Shapes match Contract A exactly.
 *
 * Scenario comes from VITE_MOCK_SCENARIO, overridable at runtime with ?mock=<name>.
 */

import authMe from '../../mocks/auth_me.json'
import authMeUnauthenticated from '../../mocks/auth_me_unauthenticated.json'
import threadsPage1 from '../../mocks/threads_page1.json'
import threadsPage2 from '../../mocks/threads_page2.json'
import threadsEmpty from '../../mocks/threads_empty.json'
import threadDetails from '../../mocks/thread_details.json'
import styleStatus from '../../mocks/style_status.json'
import runsFixture from '../../mocks/runs.json'
import errors from '../../mocks/errors.json'
import { ApiError } from './errors.js'

export const SCENARIOS = [
  'default',
  'empty',
  'unauthenticated',
  'auth-expired',
  'upstream-error',
  'slow-run',
  'style-failed',
]

export function currentScenario() {
  const fromUrl = new URLSearchParams(window.location.search).get('mock')
  const scenario = fromUrl || import.meta.env.VITE_MOCK_SCENARIO || 'default'
  return SCENARIOS.includes(scenario) ? scenario : 'default'
}

const SCENARIO = currentScenario()
const AUTH_KEY = 'draftagent.mock.authenticated'
const SEED_STARTED_KEY = 'draftagent.mock.seedStartedAt'
const SEED_MS = 9000

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function fail(code) {
  const fixture = errors[code]
  throw new ApiError({ code, status: fixture.status, message: fixture.error.message })
}

function isSignedIn() {
  if (SCENARIO === 'unauthenticated') return sessionStorage.getItem(AUTH_KEY) === 'true'
  return sessionStorage.getItem(AUTH_KEY) !== 'false'
}

/** Threads that have no hand-written fixture get one synthesised from their list row. */
function synthesiseThread(id) {
  const row = [...threadsPage1.threads, ...threadsPage2.threads].find((t) => t.id === id)
  if (!row) return null
  return {
    id: row.id,
    subject: row.subject,
    messages: [
      {
        id: `${row.id}-1`,
        from: `${row.from_name} <${row.from_email}>`,
        to: [authMe.email],
        date: row.last_message_at,
        body_text: `${row.snippet}\n\nLet me know what you think.\n\n${row.from_name.split(' ')[0]}`,
      },
    ],
  }
}

export const mockClient = {
  async getMe() {
    await sleep(250)
    if (!isSignedIn()) return authMeUnauthenticated
    return authMe
  },

  // No OAuth redirect in mocks: flip the flag, start the seed clock, reload.
  async startLogin() {
    sessionStorage.setItem(AUTH_KEY, 'true')
    sessionStorage.setItem(SEED_STARTED_KEY, String(Date.now()))
    await sleep(400)
    window.location.reload()
  },

  async logout() {
    await sleep(200)
    sessionStorage.setItem(AUTH_KEY, 'false')
    sessionStorage.removeItem(SEED_STARTED_KEY)
    return { ok: true }
  },

  async listThreads({ pageToken } = {}) {
    await sleep(500)
    if (SCENARIO === 'auth-expired') fail('AUTH_EXPIRED')
    if (SCENARIO === 'empty') return threadsEmpty
    return pageToken === 'mock-page-2' ? threadsPage2 : threadsPage1
  },

  async getThread(id) {
    await sleep(350)
    const thread = threadDetails[id] || synthesiseThread(id)
    if (!thread) fail('NOT_FOUND')
    return thread
  },

  async getStyleStatus() {
    await sleep(150)
    if (SCENARIO === 'style-failed') return styleStatus.failed
    const startedAt = Number(sessionStorage.getItem(SEED_STARTED_KEY) || 0)
    if (!startedAt) return styleStatus.ready
    return Date.now() - startedAt < SEED_MS ? styleStatus.running : styleStatus.ready
  },

  async startRun(gmailThreadId) {
    await sleep(SCENARIO === 'slow-run' ? 5000 : 1500)
    if (SCENARIO === 'upstream-error') fail('UPSTREAM_ERROR')
    const question = runsFixture.questions[gmailThreadId] || runsFixture.questions.default
    return {
      run_id: `${authMe.email}:${gmailThreadId}:${Math.random().toString(16).slice(2, 10)}`,
      status: 'awaiting_input',
      question,
    }
  },

  async resumeRun(runId, answer) {
    await sleep(2000)
    const gmailThreadId = runId.split(':')[1]
    const templates = runsFixture.drafts[gmailThreadId] || runsFixture.drafts.default
    const text = answer
      ? templates.with_answer.replace('{{answer}}', answer.trim())
      : templates.without_answer
    return {
      run_id: runId,
      status: 'completed',
      draft: { text, gmail_draft_id: runsFixture.gmail_draft_id },
    }
  },
}
