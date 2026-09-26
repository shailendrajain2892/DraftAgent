import { useCallback, useRef, useState } from 'react'
import { api, isAuthError } from '../api'

/**
 * The draft flow: POST /runs -> question -> POST /runs/{id}/resume -> draft.
 *
 * run_id only lives here in component state. A page reload mid-run loses the
 * run, which is fine for the MVP.
 */
const IDLE = { stage: 'idle', runId: null, question: null, draft: null, error: null, threadId: null }

export function useDraftRun({ onAuthError }) {
  const [run, setRun] = useState(IDLE)
  const runRef = useRef(IDLE)

  const update = useCallback((next) => {
    runRef.current = next
    setRun(next)
  }, [])

  const start = useCallback(
    async (threadId) => {
      update({ ...IDLE, stage: 'starting', threadId })
      try {
        const data = await api.startRun(threadId)
        update({ ...IDLE, stage: 'question', threadId, runId: data.run_id, question: data.question })
      } catch (error) {
        if (isAuthError(error)) onAuthError()
        else update({ ...IDLE, stage: 'error', threadId, error })
      }
    },
    [onAuthError, update],
  )

  /** `answer` is null when the user skips. */
  const answer = useCallback(
    async (text) => {
      const { runId, threadId, question } = runRef.current
      update({ ...runRef.current, stage: 'drafting', error: null })
      try {
        const data = await api.resumeRun(runId, text ?? null)
        update({ ...IDLE, stage: 'done', threadId, runId, draft: data.draft })
      } catch (error) {
        if (isAuthError(error)) onAuthError()
        else update({ ...IDLE, stage: 'error', threadId, runId, question, error })
      }
    },
    [onAuthError, update],
  )

  const reset = useCallback(() => update(IDLE), [update])

  /** Retry after an error: back to the question if we still have one, else re-run. */
  const retry = useCallback(() => {
    const current = runRef.current
    if (current.runId && current.question) update({ ...current, stage: 'question', error: null })
    else if (current.threadId) start(current.threadId)
    else update(IDLE)
  }, [start, update])

  return {
    run,
    start,
    answer,
    reset,
    retry,
    busy: run.stage === 'starting' || run.stage === 'drafting',
  }
}
