import { GMAIL_DRAFTS_URL } from '../api'
import { Modal } from './Modal.jsx'
import { CheckIcon, ExternalIcon } from './icons.jsx'

/** Paragraphs so each one can ink itself in, in sequence. */
function paragraphs(text = '') {
  return text
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter(Boolean)
}

/** The finished draft. It is already saved in Gmail - we only show it here. */
export function DraftReview({ draft, subject, pairsCount, onDone }) {
  const lines = paragraphs(draft.text)

  return (
    <Modal title={null} onClose={onDone} wide labelledBy="draft-title">
      <div className="draft-head">
        <div>
          <span className="pill" style={{ background: 'var(--ok-bg)', color: 'var(--ok-ink)' }}>
            <CheckIcon size={15} />
            Saved to Gmail drafts · never sent
          </span>
          <h2 className="modal-title" id="draft-title" style={{ margin: '14px 0 6px', fontSize: 34 }}>
            Written in your voice
          </h2>
          {subject ? (
            <p style={{ margin: 0, fontSize: 14, color: 'var(--muted)' }}>Reply to {subject}</p>
          ) : null}
        </div>

        {pairsCount ? (
          <div className="draft-stat">
            <span>Learned from</span>
            <b>{pairsCount}</b>
            <span>of your past replies</span>
          </div>
        ) : null}
      </div>

      <div className="draft-text">
        {lines.length > 0 ? (
          lines.map((line, index) => <p key={index}>{line}</p>)
        ) : (
          <p>{draft.text}</p>
        )}
      </div>

      <div className="modal-actions">
        <button type="button" className="btn btn-quiet" onClick={onDone} style={{ marginRight: 'auto' }}>
          Draft another
        </button>
        <a className="btn btn-warm" href={GMAIL_DRAFTS_URL} target="_blank" rel="noreferrer">
          Open Gmail drafts
          <ExternalIcon size={16} />
        </a>
      </div>

      {draft.gmail_draft_id ? <p className="draft-id">Gmail draft id: {draft.gmail_draft_id}</p> : null}
    </Modal>
  )
}
