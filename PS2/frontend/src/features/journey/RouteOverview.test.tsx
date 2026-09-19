import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RouteOverview } from './RouteOverview'

describe('RouteOverview', () => {
  it('renders a labelled schematic from actual journey legs', () => {
    render(<RouteOverview legs={[
      { mode: 'walk', from: { name: 'Home' }, to: { name: 'Bedok MRT' } },
      { mode: 'rail', from: { name: 'Bedok MRT' }, to: { name: 'Outram Park' }, line: { name: 'East–West Line' } },
      { mode: 'walk', from: { name: 'Outram Park' }, to: { name: 'Singapore General Hospital' } },
    ]} />)

    expect(screen.getByText(/home.*bedok mrt.*outram park.*singapore general hospital/i)).toBeVisible()
    expect(screen.getByText(/schematic.*not to scale/i)).toBeVisible()
  })
})
