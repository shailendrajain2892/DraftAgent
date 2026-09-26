import { useCallback, useEffect, useState } from 'react'
import { api, isAuthError } from '../api'

/** Preview of the selected thread. Selecting a row sends nothing to the agent. */
export function useThread(threadId, { onAuthError }) {
  const [thread, setThread] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    if (!threadId) {
      setThread(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      setThread(await api.getThread(threadId))
    } catch (err) {
      if (isAuthError(err)) onAuthError()
      else setError(err)
      setThread(null)
    } finally {
      setLoading(false)
    }
  }, [threadId, onAuthError])

  useEffect(() => {
    load()
  }, [load])

  return { thread, loading, error, retry: load }
}
