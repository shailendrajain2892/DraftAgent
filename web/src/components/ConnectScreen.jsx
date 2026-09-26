import { api } from '../api'
import { ErrorNotice } from './ErrorNotice.jsx'

/** Screen 1: app name and a single Connect Gmail button. */
export function ConnectScreen({ expired, error, onRetry }) {
  return (
    <main className="connect">
      <div className="connect-card">
        <div className="brand-mark" aria-hidden="true">
          DA
        </div>
        <h1>DraftAgent</h1>
        <p className="connect-lede">
          Reads a full Gmail thread, asks you for anything it is missing, and writes the reply in your
          own voice. The draft lands in Gmail. Nothing is ever sent for you.
        </p>

        {expired ? (
          <p className="notice notice-warn" role="status">
            Your session expired. Please connect Gmail again.
          </p>
        ) : null}

        <ErrorNotice error={error} onRetry={onRetry} />

        <button type="button" className="btn btn-primary btn-lg" onClick={() => api.startLogin()}>
          Connect Gmail
        </button>

        <p className="connect-fineprint">
          We read your recent mail to learn how you write and save drafts back to Gmail.
        </p>
      </div>
    </main>
  )
}
