import { useCallback, useEffect, useRef, useState } from 'react'
import { api, isAuthError } from '../api'

/**
 * Paged inbox list. One page up front, more only when the user asks -
 * `next_page_token` drives Load more.
 */
export function useThreads({ onAuthError }) {
  const [threads, setThreads] = useState([])
  const [nextPageToken, setNextPageToken] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState(null)
  const seenIds = useRef(new Set())

  const fetchPage = useCallback(
    async (pageToken) => {
      const first = !pageToken
      first ? setLoading(true) : setLoadingMore(true)
      setError(null)
      try {
        const data = await api.listThreads({ pageToken })
        const incoming = data.threads ?? []
        if (first) {
          seenIds.current = new Set(incoming.map((t) => t.id))
          setThreads(incoming)
        } else {
          const fresh = incoming.filter((t) => !seenIds.current.has(t.id))
          fresh.forEach((t) => seenIds.current.add(t.id))
          setThreads((current) => [...current, ...fresh])
        }
        setNextPageToken(data.next_page_token ?? null)
      } catch (err) {
        if (isAuthError(err)) onAuthError()
        else setError(err)
      } finally {
        first ? setLoading(false) : setLoadingMore(false)
      }
    },
    [onAuthError],
  )

  useEffect(() => {
    fetchPage(null)
  }, [fetchPage])

  return {
    threads,
    loading,
    loadingMore,
    error,
    hasMore: Boolean(nextPageToken),
    loadMore: () => fetchPage(nextPageToken),
    reload: () => fetchPage(null),
  }
}
