/** The voice ribbon: shown while the style store seeds, gone once it is ready. */
export function StyleBanner({ status }) {
  if (!status || status.state === 'ready' || status.state === 'not_started') return null

  if (status.state === 'failed') {
    return (
      <div className="style-banner style-banner-warn" role="status">
        <span>
          We could not build your voice profile. Drafts will use a neutral tone.
          {status.error ? ` (${status.error})` : ''}
        </span>
      </div>
    )
  }

  // The seed has no total to count towards, so the bar tracks what has been read
  // against the 300-pair cap the backend seeds with (SEED_MAX_PAIRS).
  const read = status.pairs_count ?? 0
  const width = `${Math.min(96, Math.max(6, (read / 300) * 100))}%`

  return (
    <div className="style-banner" role="status">
      <span className="pulse-dot" aria-hidden="true" />
      <span>Learning your voice — reading the last {status.window_days ?? 30} days of replies</span>
      <span className="ribbon-track" aria-hidden="true">
        <span className="ribbon-fill" style={{ width }} />
      </span>
      {read ? <span className="ribbon-count">{read} replies</span> : null}
      <span className="ribbon-note">You can draft while this runs</span>
    </div>
  )
}
