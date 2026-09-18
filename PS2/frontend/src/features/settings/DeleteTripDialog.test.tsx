import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { DeleteTripDialog } from './DeleteTripDialog'

describe('DeleteTripDialog', () => {
  it('explains that deleting removes the saved server journey', () => {
    render(<DeleteTripDialog open onClose={vi.fn()} onConfirm={vi.fn()} returnFocusRef={{ current: null }} />)

    expect(screen.getByText(/server copy.*this device/i)).toBeVisible()
    expect(screen.getByRole('button', { name: /delete journey/i })).toBeVisible()
  })
})
