import { useEffect, useRef } from 'react'

/** Dialog shell used by the question step and the draft review. */
export function Modal({ title, children, onClose, labelledBy = 'modal-title' }) {
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
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby={labelledBy} ref={panel} tabIndex={-1}>
        <h2 className="modal-title" id={labelledBy}>
          {title}
        </h2>
        {children}
      </div>
    </div>
  )
}
