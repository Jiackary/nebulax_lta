import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { AlternativesPage } from './AlternativesPage'

describe('AlternativesPage', () => {
  it('uses option-shaped placeholders while alternatives load', () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => undefined)))

    render(<MemoryRouter><AlternativesPage tripId="trip-1" /></MemoryRouter>)

    expect(screen.getByText(/checking other ways to travel/i)).toBeVisible()
    expect(screen.getAllByLabelText(/travel option is loading/i)).toHaveLength(2)
  })
})
