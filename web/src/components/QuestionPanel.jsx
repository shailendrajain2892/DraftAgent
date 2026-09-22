import { useState } from 'react'
import { ErrorNotice } from './ErrorNotice.jsx'
import { Modal } from './Modal.jsx'
import { Spinner } from './Spinner.jsx'

/**
 * The interrupt step. Continue sends the text, Skip sends null - both go to
 * POST /runs/{run_id}/resume.
 */
export function QuestionPanel({ question, busy, error, onContinue, onSkip, onRetry, onCancel }) {
  const [text, setText] = useState('')

  return (
    <Modal title="One question before I draft" onClose={busy ? undefined : onCancel}>
      <p className="question-text">{question}</p>

      <textarea
        className="answer-box"
        rows={4}
        value={text}
        disabled={busy}
        placeholder="Optional - anything the agent should know"
        onChange={(event) => setText(event.target.value)}
        aria-label="Your answer"
        autoFocus
      />

      <ErrorNotice error={error} onRetry={onRetry} inline />

      <div className="modal-actions">
        <button type="button" className="btn btn-quiet" onClick={onSkip} disabled={busy}>
          Skip
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => onContinue(text.trim() || null)}
          disabled={busy}
        >
          {busy ? <Spinner size="sm" label="Writing the draft" /> : 'Continue'}
        </button>
      </div>
    </Modal>
  )
}
