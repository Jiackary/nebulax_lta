import { describe, expect, it } from 'vitest'

import { formatSingaporeDateTime, singaporeDateTimeToIso, validateSingaporeDateTime } from './singaporeTime'

describe('Singapore appointment time', () => {
  it('keeps a chosen wall time in Singapore regardless of browser timezone', () => {
    expect(singaporeDateTimeToIso('2026-10-20T09:00')).toBe('2026-10-20T09:00:00+08:00')
  })

  it('formats an appointment after Singapore midnight correctly', () => {
    expect(formatSingaporeDateTime('2026-10-20T16:30:00Z')).toContain('21 October 2026')
    expect(formatSingaporeDateTime('2026-10-20T16:30:00Z')).toContain('00:30')
  })

  it('rejects an incomplete date-time value', () => {
    expect(validateSingaporeDateTime('2026-10-20T09')).toBe('Choose an appointment date and time.')
  })
})
