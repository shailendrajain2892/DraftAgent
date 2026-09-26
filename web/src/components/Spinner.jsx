export function Spinner({ label, size = 'md' }) {
  return (
    <span className="spinner-wrap">
      <span className={`spinner spinner-${size}`} aria-hidden="true" />
      {label ? <span className="spinner-label">{label}</span> : null}
      <span className="sr-only">{label || 'Loading'}</span>
    </span>
  )
}
