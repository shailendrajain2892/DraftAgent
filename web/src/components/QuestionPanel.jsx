import { useState } from 'react'
import { BrandMark } from './BrandMark.jsx'
import { ErrorNotice } from './ErrorNotice.jsx'
import { Modal } from './Modal.jsx'
import { Spinner } from './Spinner.jsx'
import { ArrowIcon, LockIcon } from './icons.jsx'

/**
 * The interrupt step. Continue sends the text, Skip sends null - both go to
 * POST /runs/{run_id}/resume.
 */
export function QuestionPanel({
  question,
  busy,
  error,
  messageCount,
  onContinue,
  onSkip,
  onRetry,
  onCancel,
}) {
  const [text, setText] = useState('')

  return (
    <Modal title="One thing before I write" onClose={busy ? undefined : onCancel}>
      <div className="modal-agent" style={{ marginTop: -6 }}>
        <BrandMark size={48} />
        <span className="agent-kicker">
          <b>DraftAgent</b>
          <span>{messageCount ? `Read ${messageCount} messages in this thread` : 'Read the thread'}</span>
        </span>
      </div>

      <p className="question-text">{question}</p>

      <label className="field-label" htmlFor="answer">
        Your answer — optional
      </label>
      <textarea
        id="answer"
        className="answer-box"
        rows={3}
        value={text}
        disabled={busy}
        placeholder="Anything I should know before drafting"
        onChange={(event) => setText(event.target.value)}
        autoFocus
      />

      <ErrorNotice error={error} onRetry={onRetry} inline />

      <div className="modal-actions">
        <span className="modal-foot-note">
          <LockIcon size={14} />
          Nothing is sent
        </span>
        <button type="button" className="btn btn-quiet" onClick={onSkip} disabled={busy}>
          Skip
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => onContinue(text.trim() || null)}
          disabled={busy}
        >
          {busy ? (
            <Spinner size="sm" label="Writing the draft" />
          ) : (
            <>
              Write it
              <ArrowIcon size={17} />
            </>
          )}
        </button>
      </div>
    </Modal>
  )
}
