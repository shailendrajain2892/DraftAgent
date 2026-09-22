import { GMAIL_DRAFTS_URL } from '../api'
import { Modal } from './Modal.jsx'

/** The finished draft. It is already saved in Gmail - we only show it here. */
export function DraftReview({ draft, onDone }) {
  return (
    <Modal title="Your draft is ready" onClose={onDone}>
      <p className="notice notice-ok" role="status">
        Saved to your Gmail drafts. Nothing has been sent.
      </p>

      <div className="draft-text">{draft.text}</div>

      <div className="modal-actions">
        <a className="btn btn-quiet" href={GMAIL_DRAFTS_URL} target="_blank" rel="noreferrer">
          Open Gmail drafts
        </a>
        <button type="button" className="btn btn-primary" onClick={onDone}>
          Draft another
        </button>
      </div>

      {draft.gmail_draft_id ? <p className="draft-id">Gmail draft id: {draft.gmail_draft_id}</p> : null}
    </Modal>
  )
}
