import { useCallback, useEffect, useRef, useState } from 'react'
import { api, isAuthError } from '../api'

const POLL_MS = 3000

/**
 * Seed progress for the style store. Polls every 3s while `running`.
 * Drafting is allowed during the seed - the agent falls back to a default style.
 */
export function useStyleStatus({ onAuthError }) {
  const [status, setStatus] = useState(null)
  const timer = useRef(null)

  const poll = useCallback(async () => {
    try {
      const data = await api.getStyleStatus()
      setStatus(data)
      if (data?.state === 'running') {
        timer.current = setTimeout(poll, POLL_MS)
      }
    } catch (err) {
      if (isAuthError(err)) onAuthError()
      // A failed status poll is not worth interrupting the user for: the banner
      // just stays hidden.
    }
  }, [onAuthError])

  useEffect(() => {
    poll()
    return () => clearTimeout(timer.current)
  }, [poll])

  return status
}
