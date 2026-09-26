import { canRetry, uiMessage } from '../api'

/** Every failed call shows a short message and a Retry button. */
export function ErrorNotice({ error, onRetry, retryLabel = 'Retry', inline = false }) {
  if (!error) return null
  return (
    <div className={inline ? 'error-notice error-notice-inline' : 'error-notice'} role="alert">
      <div className="error-text">
        <strong>{uiMessage(error)}</strong>
        {error.code && error.code !== 'UNKNOWN' ? <code className="error-code">{error.code}</code> : null}
      </div>
      {onRetry && canRetry(error) ? (
        <button type="button" className="btn btn-quiet" onClick={onRetry}>
          {retryLabel}
        </button>
      ) : null}
    </div>
  )
}
