// Backend place names are full postal descriptions: "Singapore General Hospital Outram
// Campus, Block 3 Specialist Outpatient Clinic, Level 4 Counter B". On a 320px phone one of
// those set as a heading is five lines of bold text, and in a schematic's 64px column it is
// unreadable however it wraps. These shorten it for display only — the full name is always
// still on the screen, in the written instruction and in the diagram's description.

/** The identifying part of a name: everything before the first comma, with any parenthetical
 *  line list removed. "Outram Park Interchange (East-West, North-East and Thomson-East Coast
 *  Lines)" becomes "Outram Park Interchange". */
export function placeName(name: string) {
  // The parenthetical goes first. "Outram Park Interchange (East-West, North-East …)" has a
  // comma inside the brackets, so splitting on the comma first leaves a dangling "(East-West"
  // that the bracket strip can no longer match.
  const base = name.replace(/\s*\([^)]*\)\s*/g, ' ').split(',')[0].replace(/\s+/g, ' ').trim()
  return base || name.trim()
}

/** The same, cut to whole words at a budget. Only ever shorter than what `placeName` gives,
 *  and the ellipsis says out loud that something was left off. */
export function shortPlaceName(name: string, max: number) {
  const base = placeName(name)
  if (base.length <= max) return base
  const words = base.split(' ')
  let out = ''
  for (const word of words) {
    const next = out ? `${out} ${word}` : word
    if (out && next.length > max) break
    out = next
  }
  return `${out || base.slice(0, max)}…`
}
