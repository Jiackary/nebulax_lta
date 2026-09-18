import type { RefObject } from 'react'

import { Dialog } from '../../components/Dialog'

export function DeleteTripDialog({ open, onClose, onConfirm, returnFocusRef }: { open: boolean; onClose: () => void; onConfirm: () => void; returnFocusRef: RefObject<HTMLElement | null> }) {
  return (
    <Dialog open={open} title="Delete this journey?" onClose={onClose} returnFocusRef={returnFocusRef}>
      <p>This removes the server copy and the saved journey on this device. It cannot be undone.</p>
      <div className="dialog-actions"><button className="button button-secondary" type="button" onClick={onClose}>Keep journey</button><button className="button button-danger" type="button" onClick={onConfirm}>Delete journey</button></div>
    </Dialog>
  )
}
