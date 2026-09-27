/**
 * The DraftAgent mark: a nib that is also a leaf.
 * One closed curve, one stroke down the middle, one ink dot.
 *
 * `variant="tile"` draws the espresso rounded square behind it (headers,
 * connect screen). `variant="bare"` is the leaf alone, for use on a surface
 * that already provides the dark ground, like the rail.
 */
export function BrandMark({ size = 40, variant = 'tile', className }) {
  const leafColor = 'var(--sage)'
  const slitColor = variant === 'tile' ? 'var(--espresso)' : 'var(--espresso)'

  return (
    <svg
      className={className}
      viewBox="0 0 64 64"
      width={size}
      height={size}
      aria-hidden="true"
      focusable="false"
    >
      {variant === 'tile' ? (
        <rect width="64" height="64" rx="19" fill="var(--espresso)" />
      ) : null}
      <path
        d="M32 13c11 9.5 15 18.5 15 25.2C47 47 40.3 53 32 53s-15-6-15-14.8C17 31.5 21 22.5 32 13z"
        fill={leafColor}
      />
      {/* Below ~20px these two vanish and the silhouette carries the mark. */}
      <path d="M32 22v24" stroke={slitColor} strokeWidth="2.6" strokeLinecap="round" />
      <circle cx="32" cy="41" r="3.4" fill={slitColor} />
    </svg>
  )
}
