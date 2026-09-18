import { render, screen } from '@testing-library/react'

import App from './App'

describe('application shell', () => {
  afterEach(() => {
    window.history.replaceState({}, '', '/')
  })

  it('gives a mobile visitor a clear way to plan a journey', () => {
    render(<App />)

    expect(screen.getByRole('link', { name: /plan journey/i })).toBeVisible()
  })

  it('recovers from an unknown deep link', () => {
    window.history.replaceState({}, '', '/not-a-route')
    render(<App />)

    expect(screen.getByRole('heading', { name: /page not found/i })).toBeVisible()
    expect(screen.getByRole('link', { name: /go home/i })).toHaveAttribute('href', '/')
  })
})
