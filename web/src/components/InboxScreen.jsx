import { useState } from 'react'
import { useDraftRun } from '../hooks/useDraftRun.js'
import { useStyleStatus } from '../hooks/useStyleStatus.js'
import { useThread } from '../hooks/useThread.js'
import { useThreads } from '../hooks/useThreads.js'
import { initials } from '../utils/format.js'
import { BrandMark } from './BrandMark.jsx'
import { DraftReview } from './DraftReview.jsx'
import { ErrorNotice } from './ErrorNotice.jsx'
import { Modal } from './Modal.jsx'
import { QuestionPanel } from './QuestionPanel.jsx'
import { Spinner } from './Spinner.jsx'
import { StyleBanner } from './StyleBanner.jsx'
import { ThreadList } from './ThreadList.jsx'
import { ThreadPreview } from './ThreadPreview.jsx'
import { InboxIcon, NibIcon, SignOutIcon } from './icons.jsx'

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

  const thread = preview.thread

  return (
    <div className="app-shell">
      <nav className="rail" aria-label="Sections">
        <BrandMark size={38} variant="bare" />
        <div className="rail-nav">
          <button type="button" className="rail-btn is-active" aria-label="Inbox" aria-current="page">
            <InboxIcon size={21} />
          </button>
          <a
            className="rail-btn"
            href="https://mail.google.com/mail/u/0/#drafts"
            target="_blank"
            rel="noreferrer"
            aria-label="Your Gmail drafts"
          >
            <NibIcon size={21} />
          </a>
        </div>
        <div className="rail-spacer" />
        <button type="button" className="rail-btn" onClick={onSignOut} aria-label="Sign out">
          <SignOutIcon size={21} />
        </button>
        <span className="avatar avatar-sm" style={{ background: 'var(--clay)', color: 'var(--clay-ink)' }}>
          {initials(email)}
        </span>
      </nav>

      <div className="app-main">
        <header className="topbar">
          <span className="topbar-title">DraftAgent</span>
          <div className="topbar-right" style={{ marginLeft: 'auto' }}>
            <span className="account">{email}</span>
            <span className="avatar avatar-sm" style={{ background: 'var(--sky)', color: 'var(--sky-ink)' }}>
              {initials(email)}
            </span>
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
            {thread ? (
              <div className="preview-actions">
                <div className="preview-head">
                  <h1>{thread.subject}</h1>
                  <p className="preview-meta">
                    <span>
                      {thread.messages.length} message{thread.messages.length === 1 ? '' : 's'}
                    </span>
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy || run.stage !== 'idle'}
                  onClick={() => start(selectedId)}
                >
                  {run.stage === 'starting' ? (
                    <Spinner size="sm" label="Reading the thread" />
                  ) : (
                    <>
                      <NibIcon size={18} />
                      Draft reply
                    </>
                  )}
                </button>
              </div>
            ) : null}

            {run.stage === 'starting' ? (
              <p className="hint" style={{ padding: '0 34px 14px' }}>
                This usually takes 10 to 30 seconds.
              </p>
            ) : null}

            <ThreadPreview
              thread={thread}
              loading={preview.loading}
              error={preview.error}
              onRetry={preview.error?.code === 'NOT_FOUND' ? clearMissingThread : preview.retry}
              selectedId={selectedId}
              accountEmail={email}
            />
          </section>
        </main>
      </div>

      {run.stage === 'question' || run.stage === 'drafting' ? (
        <QuestionPanel
          question={run.question}
          busy={busy}
          messageCount={thread?.messages?.length}
          onContinue={(text) => answer(text)}
          onSkip={() => answer(null)}
          onCancel={reset}
        />
      ) : null}

      {run.stage === 'done' && run.draft ? (
        <DraftReview
          draft={run.draft}
          subject={thread?.subject}
          pairsCount={styleStatus?.pairs_count}
          onDone={draftAnother}
        />
      ) : null}

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
