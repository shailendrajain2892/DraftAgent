/** Shown while the style store seeds; hidden once it is ready. */
export function StyleBanner({ status }) {
  if (!status || status.state === 'ready' || status.state === 'not_started') return null

  if (status.state === 'failed') {
    return (
      <div className="style-banner style-banner-warn" role="status">
        <span>
          We could not build your style profile. Drafts will use a neutral tone.
          {status.error ? ` (${status.error})` : ''}
        </span>
      </div>
    )
  }

  return (
    <div className="style-banner" role="status">
      <span className="spinner spinner-sm" aria-hidden="true" />
      <span>
        Building your style profile from the last {status.window_days ?? 30} days
        {status.pairs_count ? ` - ${status.pairs_count} replies so far` : ''}. You can start drafting now.
      </span>
    </div>
  )
}
