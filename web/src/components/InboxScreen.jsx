import { useState } from 'react'
import { useDraftRun } from '../hooks/useDraftRun.js'
import { useStyleStatus } from '../hooks/useStyleStatus.js'
import { useThread } from '../hooks/useThread.js'
import { useThreads } from '../hooks/useThreads.js'
import { DraftReview } from './DraftReview.jsx'
import { ErrorNotice } from './ErrorNotice.jsx'
import { Modal } from './Modal.jsx'
import { QuestionPanel } from './QuestionPanel.jsx'
import { Spinner } from './Spinner.jsx'
import { StyleBanner } from './StyleBanner.jsx'
import { ThreadList } from './ThreadList.jsx'
import { ThreadPreview } from './ThreadPreview.jsx'

export function InboxScreen({ email, onSignOut, onAuthError }) {
  const [selectedId, setSelectedId] = useState(null)

  const list = useThreads({ onAuthError })
  const preview = useThread(selectedId, { onAuthError })
  const styleStatus = useStyleStatus({ onAuthError })
  const { run, start, answer, reset, retry, busy } = useDraftRun({ onAuthError })

  // NOT_FOUND on a preview means the thread is gone: drop the selection.
  const clearMissingThread = () => {
    setSelectedId(null)
    list.reload()
  }

  const draftAnother = () => {
    reset()
    setSelectedId(null)
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark brand-mark-sm" aria-hidden="true">
            DA
          </span>
          <span className="brand-name">DraftAgent</span>
        </div>
        <div className="topbar-right">
          <span className="account">{email}</span>
          <button type="button" className="btn btn-quiet btn-sm" onClick={onSignOut}>
            Sign out
          </button>
        </div>
      </header>

      <StyleBanner status={styleStatus} />

      <main className="panes">
        <section className="pane pane-list" aria-label="Threads">
          <ThreadList
            threads={list.threads}
            loading={list.loading}
            loadingMore={list.loadingMore}
            error={list.error}
            hasMore={list.hasMore}
            onLoadMore={list.loadMore}
            onReload={list.reload}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </section>

        <section className="pane pane-preview" aria-label="Thread preview">
          <div className="preview-actions">
            <button
              type="button"
              className="btn btn-primary"
              disabled={!selectedId || busy || run.stage !== 'idle'}
              onClick={() => start(selectedId)}
            >
              {run.stage === 'starting' ? <Spinner size="sm" label="Reading the thread" /> : 'Draft reply'}
            </button>
            {run.stage === 'starting' ? (
              <span className="hint">This usually takes 10 to 30 seconds.</span>
            ) : null}
          </div>

          <ThreadPreview
            thread={preview.thread}
            loading={preview.loading}
            error={preview.error}
            onRetry={preview.error?.code === 'NOT_FOUND' ? clearMissingThread : preview.retry}
            selectedId={selectedId}
          />
        </section>
      </main>

      {run.stage === 'question' || run.stage === 'drafting' ? (
        <QuestionPanel
          question={run.question}
          busy={busy}
          onContinue={(text) => answer(text)}
          onSkip={() => answer(null)}
          onCancel={reset}
        />
      ) : null}

      {run.stage === 'done' && run.draft ? <DraftReview draft={run.draft} onDone={draftAnother} /> : null}

      {run.stage === 'error' ? (
        <Modal title="That did not work" onClose={reset}>
          <ErrorNotice error={run.error} onRetry={retry} />
          <div className="modal-actions">
            <button type="button" className="btn btn-quiet" onClick={reset}>
              Close
            </button>
          </div>
        </Modal>
      ) : null}
    </div>
  )
}
