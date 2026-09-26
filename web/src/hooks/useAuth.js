import { useCallback, useEffect, useState } from 'react'
import { api, isAuthError } from '../api'

/**
 * Who is signed in. `GET /auth/me` on mount; any 401 anywhere in the app
 * calls `onAuthError` and drops back to the Connect screen.
 */
export function useAuth() {
  const [state, setState] = useState({ status: 'loading', email: null, expired: false, error: null })

  const check = useCallback(async () => {
    setState((s) => ({ ...s, status: 'loading', error: null }))
    try {
      const me = await api.getMe()
      setState({
        status: me?.authenticated ? 'signed-in' : 'signed-out',
        email: me?.email ?? null,
        expired: false,
        error: null,
      })
    } catch (error) {
      if (isAuthError(error)) {
        setState({ status: 'signed-out', email: null, expired: true, error: null })
      } else {
        setState({ status: 'error', email: null, expired: false, error })
      }
    }
  }, [])

  useEffect(() => {
    check()
  }, [check])

  const signOut = useCallback(async () => {
    try {
      await api.logout()
    } finally {
      setState({ status: 'signed-out', email: null, expired: false, error: null })
    }
  }, [])

  /** Called by any screen that sees a 401. */
  const onAuthError = useCallback(() => {
    setState({ status: 'signed-out', email: null, expired: true, error: null })
  }, [])

  return { ...state, check, signOut, onAuthError }
}
