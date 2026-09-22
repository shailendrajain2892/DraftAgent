import { initials, shortTime } from '../utils/format.js'
import { ErrorNotice } from './ErrorNotice.jsx'
import { Spinner } from './Spinner.jsx'

/** Left pane: one page at a time, Load more uses next_page_token. */
export function ThreadList({
  threads,
  loading,
  loadingMore,
  error,
  hasMore,
  onLoadMore,
  onReload,
  selectedId,
  onSelect,
}) {
  if (loading) {
    return (
      <div className="list-state">
        <Spinner label="Loading your inbox" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="list-state">
        <ErrorNotice error={error} onRetry={onReload} />
      </div>
    )
  }

  if (threads.length === 0) {
    return (
      <div className="list-state">
        <p className="empty-title">No threads in the last 30 days.</p>
        <button type="button" className="btn btn-quiet" onClick={onReload}>
          Refresh
        </button>
      </div>
    )
  }

  return (
    <div className="thread-list">
      <ul className="thread-rows">
        {threads.map((thread) => {
          const selected = thread.id === selectedId
          return (
            <li key={thread.id}>
              <button
                type="button"
                className={`thread-row${selected ? ' is-selected' : ''}`}
                onClick={() => onSelect(thread.id)}
                aria-current={selected ? 'true' : undefined}
                aria-label={`${thread.from_name}: ${thread.subject}`}
              >
                <span className="avatar" aria-hidden="true">
                  {initials(thread.from_name)}
                </span>
                <span className="thread-row-body">
                  <span className="thread-row-top">
                    <span className="thread-sender">{thread.from_name}</span>
                    <span className="thread-time">{shortTime(thread.last_message_at)}</span>
                  </span>
                  <span className="thread-subject">
                    {thread.subject}
                    {thread.message_count > 1 ? (
                      <span className="msg-count" title={`${thread.message_count} messages`}>
                        {thread.message_count}
                      </span>
                    ) : null}
                  </span>
                  <span className="thread-snippet">{thread.snippet}</span>
                </span>
              </button>
            </li>
          )
        })}
      </ul>

      {hasMore ? (
        <div className="list-footer">
          <button type="button" className="btn btn-quiet" onClick={onLoadMore} disabled={loadingMore}>
            {loadingMore ? <Spinner size="sm" label="Loading" /> : 'Load more'}
          </button>
        </div>
      ) : (
        <p className="list-end">That is everything from the last 30 days.</p>
      )}
    </div>
  )
}
