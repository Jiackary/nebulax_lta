import { useEffect, useRef, type ReactNode, type RefObject } from 'react'

type DialogProps = {
  children: ReactNode
  open: boolean
  title: string
  onClose: () => void
  returnFocusRef?: RefObject<HTMLElement | null>
}

export function Dialog({ children, open, title, onClose, returnFocusRef }: DialogProps) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const wasOpen = useRef(false)

  useEffect(() => {
    if (open) {
      wasOpen.current = true
      closeRef.current?.focus()
      return
    }

    if (wasOpen.current) {
      returnFocusRef?.current?.focus()
      wasOpen.current = false
    }
  }, [open, returnFocusRef])

  if (!open) return null

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        onMouseDown={(event) => event.stopPropagation()}
        onKeyDown={(event) => {
          if (event.key === 'Escape') onClose()
          if (event.key === 'Tab') {
            const controls = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]'))
            const first = controls[0]
            const last = controls[controls.length - 1]
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
          }
        }}
      >
        <div className="dialog-heading">
          <h2 id="dialog-title">{title}</h2>
          <button ref={closeRef} className="dialog-close" type="button" onClick={onClose}>Close</button>
        </div>
        <div className="dialog-body">{children}</div>
      </section>
    </div>
  )
}
