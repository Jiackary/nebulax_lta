import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { JourneySkeleton } from './JourneySkeleton'

describe('JourneySkeleton', () => {
  it('exposes one loading message while reserving journey-shaped space', () => {
    render(<JourneySkeleton />)

    expect(screen.getByText(/loading your saved route/i)).toBeVisible()
    expect(screen.getByLabelText(/journey is loading/i)).toHaveAttribute('aria-busy', 'true')
  })
})
