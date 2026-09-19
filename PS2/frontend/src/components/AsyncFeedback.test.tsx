import { act, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AsyncFeedback } from './AsyncFeedback'

describe('AsyncFeedback', () => {
  afterEach(() => vi.useRealTimers())

  it('adds slow-request guidance only after five seconds of real waiting', () => {
    vi.useFakeTimers()
    render(<AsyncFeedback operation="checking-status" label="Checking current conditions…" />)

    expect(screen.getByText('Checking current conditions…')).toBeVisible()
    expect(screen.queryByText(/taking longer than usual/i)).not.toBeInTheDocument()

    act(() => vi.advanceTimersByTime(5_000))

    expect(screen.getByText(/taking longer than usual/i)).toBeVisible()
  })

  it('renders no live feedback while idle', () => {
    const { container } = render(<AsyncFeedback operation="idle" label="Loading" />)

    expect(container).toBeEmptyDOMElement()
  })
})
