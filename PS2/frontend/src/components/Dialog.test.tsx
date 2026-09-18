import { useRef, useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { Dialog } from './Dialog'

function DialogFixture() {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)

  return (
    <>
      <button ref={triggerRef} type="button" onClick={() => setOpen(true)}>Remove journey</button>
      <Dialog open={open} title="Remove this journey" onClose={() => setOpen(false)} returnFocusRef={triggerRef}>
        <p>This removes the saved journey.</p>
      </Dialog>
    </>
  )
}

describe('Dialog', () => {
  it('returns focus to its trigger after it closes', async () => {
    const user = userEvent.setup()
    render(<DialogFixture />)

    const trigger = screen.getByRole('button', { name: /remove journey/i })
    await user.click(trigger)
    expect(screen.getByRole('dialog', { name: /remove this journey/i })).toBeVisible()
    await user.tab()
    expect(screen.getByRole('button', { name: /close/i })).toHaveFocus()
    await user.tab({ shift: true })
    expect(screen.getByRole('button', { name: /close/i })).toHaveFocus()

    await user.click(screen.getByRole('button', { name: /close/i }))
    expect(trigger).toHaveFocus()
  })
})
