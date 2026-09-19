const DATETIME_LOCAL = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/

function isRealDate(year: number, month: number, day: number, hour: number, minute: number) {
  const value = new Date(Date.UTC(year, month - 1, day, hour, minute))
  return value.getUTCFullYear() === year
    && value.getUTCMonth() === month - 1
    && value.getUTCDate() === day
    && value.getUTCHours() === hour
    && value.getUTCMinutes() === minute
}

export function validateSingaporeDateTime(value: string) {
  const match = DATETIME_LOCAL.exec(value)
  if (!match) return 'Choose an appointment date and time.'
  const [, year, month, day, hour, minute] = match.map(Number)
  return isRealDate(year, month, day, hour, minute) ? null : 'Choose a valid appointment date and time.'
}

export function singaporeDateTimeToIso(value: string) {
  if (validateSingaporeDateTime(value)) throw new Error('Invalid Singapore appointment time')
  return `${value}:00+08:00`
}

export function formatSingaporeDateTime(value: string) {
  const parsed = new Date(value)
  // Intl throws on an invalid date. The screens that call this include the saved journey read
  // back with no network, where a throw would blank the written steps rather than show a stamp.
  if (Number.isNaN(parsed.getTime())) return value
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'long',
    timeStyle: 'short',
    hourCycle: 'h23',
    timeZone: 'Asia/Singapore',
  }).format(parsed)
}

/**
 * The clock face alone, for the departure lockup where the surrounding copy already says
 * what the number is. Derived from the ISO instant rather than by stripping English words
 * off the backend's label, which would break the moment that label is reworded or localised.
 * Returns null when the value cannot be parsed, so the caller can fall back to the label.
 */
export function formatSingaporeClock(value: string) {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return null
  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone: 'Asia/Singapore',
  }).format(parsed)
}
