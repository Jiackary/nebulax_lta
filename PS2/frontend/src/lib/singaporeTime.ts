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
