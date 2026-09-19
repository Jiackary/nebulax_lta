import { useEffect, useState } from 'react'

import type { JourneyOperation } from '../features/journey/journeyCoordinator'

export function AsyncFeedback({ operation, label }: { operation: JourneyOperation; label: string }) {
  if (operation === 'idle') return null
  return <TimedFeedback key={operation} label={label} />
}

function TimedFeedback({ label }: { label: string }) {
  const [slow, setSlow] = useState(false)

  useEffect(() => {
    const timer = window.setTimeout(() => setSlow(true), 5_000)
    return () => window.clearTimeout(timer)
  }, [])

  return (
    <div className="async-feedback" role="status" aria-live="polite" aria-busy="true">
      <span className="progress-line" aria-hidden="true" />
      <p>{label}</p>
      {slow && <p className="async-feedback-slow">This is taking longer than usual. You can stay on this screen.</p>}
    </div>
  )
}
