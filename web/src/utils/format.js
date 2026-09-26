/** Small display helpers. */

/** "10:42", "Fri", or "18 Sep" depending on how old the message is. */
export function shortTime(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const ageDays = (Date.now() - date.getTime()) / 86_400_000
  if (ageDays < 1) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (ageDays < 7) return date.toLocaleDateString([], { weekday: 'short' })
  return date.toLocaleDateString([], { day: 'numeric', month: 'short' })
}

export function fullTime(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString([], {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Messages carry `from` as "Name <email>". */
export function splitSender(from = '') {
  const match = from.match(/^\s*(.*?)\s*<([^>]+)>\s*$/)
  if (match) return { name: match[1] || match[2], email: match[2] }
  return { name: from, email: from }
}

export function initials(name = '') {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}
