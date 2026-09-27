import { fullTime, initials, splitSender } from '../utils/format.js'
import { tintFor } from '../utils/tint.js'
import { ErrorNotice } from './ErrorNotice.jsx'
import { Spinner } from './Spinner.jsx'

/** Right pane: the selected thread, oldest message first. */
export function ThreadPreview({ thread, loading, error, onRetry, selectedId, accountEmail }) {
  if (!selectedId) {
    return (
      <div className="preview-empty">
        <p className="empty-title">Pick a thread</p>
        <p className="empty-sub">Select a conversation on the left to read it and draft a reply.</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="preview-empty">
        <Spinner label="Loading thread" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="preview-empty">
        <ErrorNotice error={error} onRetry={onRetry} />
      </div>
    )
  }

  if (!thread) return null

  return (
    <article className="preview">
      <div className="messages">
        {thread.messages.map((message) => {
          const sender = splitSender(message.from)
          const mine = accountEmail && sender.email.toLowerCase() === accountEmail.toLowerCase()
          return (
            <section className={`message${mine ? ' message-mine' : ''}`} key={message.id}>
              <header className="message-header">
                <span className="avatar avatar-sm" style={tintFor(sender.email)}>
                  {initials(sender.name)}
                </span>
                <span className="message-who">
                  <span className="message-name">{mine ? 'You' : sender.name}</span>
                  <span className="message-to">to {message.to?.join(', ')}</span>
                </span>
                <time className="message-date" dateTime={message.date}>
                  {fullTime(message.date)}
                </time>
              </header>
              <p className="message-body">{message.body_text}</p>
            </section>
          )
        })}
      </div>
    </article>
  )
}
