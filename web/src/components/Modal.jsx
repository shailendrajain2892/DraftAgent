import { useEffect, useRef } from 'react'

/** Dialog shell: the pastel ribbon, the drift-in, Escape to close. */
export function Modal({ title, children, onClose, wide = false, labelledBy = 'modal-title' }) {
  const panel = useRef(null)

  useEffect(() => {
    panel.current?.focus()
    if (!onClose) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="modal-backdrop">
      <div
        className={`modal${wide ? ' modal-wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        ref={panel}
        tabIndex={-1}
      >
        <div className="modal-ribbon" aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>
        <div className="modal-body">
          {title ? (
            <h2 className="modal-title" id={labelledBy}>
              {title}
            </h2>
          ) : null}
          {children}
        </div>
      </div>
    </div>
  )
}
