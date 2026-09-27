import { api } from '../api'
import { BrandMark } from './BrandMark.jsx'
import { ErrorNotice } from './ErrorNotice.jsx'
import { LockIcon, MailIcon, NibIcon, ShieldIcon } from './icons.jsx'

/** Screen 1: the pitch, and one Connect Gmail button. */
export function ConnectScreen({ expired, error, onRetry }) {
  return (
    <main className="connect">
      <div className="connect-lead">
        <div className="brand">
          <BrandMark size={46} />
          <span className="brand-name">DraftAgent</span>
        </div>

        <h1 className="connect-title">Your inbox, answered in your own words.</h1>

        <p className="connect-lede">
          It reads the whole thread, asks you the one thing it cannot guess, then writes the reply
          the way you would. The draft waits in Gmail.
        </p>

        {expired ? (
          <p className="notice notice-warn" role="status">
            Your session expired. Please connect Gmail again.
          </p>
        ) : null}

        <ErrorNotice error={error} onRetry={onRetry} />

        <div className="connect-cta">
          <span className="cta-halo">
            <button type="button" className="btn btn-primary btn-lg" onClick={() => api.startLogin()}>
              <MailIcon size={19} />
              Connect Gmail
            </button>
          </span>
          <span className="cta-note">Takes a few seconds. Nothing leaves your account.</span>
        </div>

        <div className="assurances">
          <p className="assurance">
            <LockIcon size={19} />
            <span>
              <strong>Reads, never sends.</strong> No send permission is even requested.
            </span>
          </p>
          <p className="assurance">
            <NibIcon size={19} />
            <span>
              <strong>Drafts land in Gmail.</strong> Edit and send them yourself.
            </span>
          </p>
          <p className="assurance">
            <ShieldIcon size={19} />
            <span>
              <strong>Tokens stay server-side.</strong> Your browser only holds a session.
            </span>
          </p>
        </div>
      </div>

      {/* Decorative: the paper stack. */}
      <div className="connect-aside" aria-hidden="true">
        <div className="paper paper-a" />
        <div className="paper paper-b" />
        <div className="paper paper-card">
          <div className="message-header">
            <span className="avatar avatar-sm" style={{ background: 'var(--clay)', color: 'var(--clay-ink)' }}>
              PN
            </span>
            <span className="message-who">
              <span className="message-name">Priya Nair</span>
              <span className="message-to">Q3 vendor quote</span>
            </span>
            <span className="pill" style={{ background: 'var(--ok-bg)', color: 'var(--ok-ink)' }}>
              Drafted
            </span>
          </div>
          <div className="paper-lines">
            <span style={{ width: '100%' }} />
            <span style={{ width: '86%' }} />
            <span style={{ width: '62%' }} />
          </div>
          <div className="paper-foot">
            <BrandMark size={19} variant="bare" />
            Written in your voice, waiting in Gmail
          </div>
        </div>
      </div>
    </main>
  )
}
