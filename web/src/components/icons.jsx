/** Inline stroke icons, 1.8px on a 24 grid. They take the current text colour. */

const base = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: 'false',
}

export function InboxIcon({ size = 20 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} {...base}>
      <path d="M4 13h4l1.6 2.6h4.8L16 13h4" />
      <path d="M5.6 5h12.8L21 13v4.4A2.6 2.6 0 0 1 18.4 20H5.6A2.6 2.6 0 0 1 3 17.4V13z" />
    </svg>
  )
}

/** The nib, reused for drafts and for the Draft reply button. */
export function NibIcon({ size = 20 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} {...base}>
      <path d="M12 3.5c5.4 4.7 7.4 9.1 7.4 12.4A7.4 7.4 0 0 1 12 20.9a7.4 7.4 0 0 1-7.4-5C4.6 12.6 6.6 8.2 12 3.5z" />
      <path d="M12 8.4v8.2" />
    </svg>
  )
}

export function MailIcon({ size = 20 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} {...base}>
      <rect x="2.8" y="5" width="18.4" height="14" rx="2.8" />
      <path d="M3.4 7.2L12 13.4l8.6-6.2" />
    </svg>
  )
}

export function LockIcon({ size = 20 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} {...base}>
      <rect x="4" y="10.5" width="16" height="10" rx="2.6" />
      <path d="M8 10.5V7.8a4 4 0 0 1 8 0v2.7" />
    </svg>
  )
}

export function ShieldIcon({ size = 20 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} {...base}>
      <path d="M12 3.2l7.4 3v5.4c0 4.4-3 8.1-7.4 9.2-4.4-1.1-7.4-4.8-7.4-9.2V6.2z" />
    </svg>
  )
}

export function CheckIcon({ size = 20 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} {...base} strokeWidth={2.3}>
      <path d="M5 12.6l4.4 4.4L19 7.4" />
    </svg>
  )
}

export function ArrowIcon({ size = 20 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} {...base} strokeWidth={2}>
      <path d="M4.5 12h14" />
      <path d="M13 6.5l5.5 5.5L13 17.5" />
    </svg>
  )
}

export function ExternalIcon({ size = 20 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} {...base} strokeWidth={2}>
      <path d="M13 5h6v6" />
      <path d="M19 5l-8.5 8.5" />
      <path d="M18 14.5V18a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3.5" />
    </svg>
  )
}

export function SignOutIcon({ size = 20 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} {...base}>
      <path d="M14.5 7.5V5.8A1.8 1.8 0 0 0 12.7 4H5.8A1.8 1.8 0 0 0 4 5.8v12.4A1.8 1.8 0 0 0 5.8 20h6.9a1.8 1.8 0 0 0 1.8-1.8v-1.7" />
      <path d="M9.5 12h11" />
      <path d="M17.5 8.5L21 12l-3.5 3.5" />
    </svg>
  )
}
