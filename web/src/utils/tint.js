/**
 * A stable pastel per correspondent, so the same sender always keeps the same
 * avatar colour. Each pair is a fill plus text from the same hue, well past 4.5:1.
 */
const TINTS = [
  { background: '#e8c6b4', color: '#6b3a22' }, // clay
  { background: '#c9d9e8', color: '#26485f' }, // sky
  { background: '#d3c6e8', color: '#463366' }, // lilac
  { background: '#f3e2b8', color: '#6b5312' }, // wheat
  { background: '#bdd3b4', color: '#2c4423' }, // sage
]

export function tintFor(seed = '') {
  let hash = 0
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) % 9973
  }
  return TINTS[hash % TINTS.length]
}
