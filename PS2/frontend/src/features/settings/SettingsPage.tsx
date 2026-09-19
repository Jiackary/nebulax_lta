import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { ApiError } from '../../api/client'
import { deleteTrip } from '../../api/trips'
import { clearOfflineBundle } from '../offline/storage'
import { clearActiveTripId } from '../planning/activeTrip'
import { DeleteTripDialog } from './DeleteTripDialog'
import { ReminderControls } from '../push/ReminderControls'

export function SettingsPage({ tripId }: { tripId: string | null }) {
  const navigate = useNavigate()
  const deleteTrigger = useRef<HTMLButtonElement>(null)
  const [confirming, setConfirming] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  async function removeTrip() {
    if (!tripId || deleting) return
    setDeleting(true)
    let serverDeleted = false
    try {
      await deleteTrip(tripId)
      serverDeleted = true
      clearActiveTripId()
      await clearOfflineBundle(tripId)
      navigate('/')
    } catch (reason) {
      setMessage(serverDeleted
        ? 'The server journey was deleted, but the saved copy on this device could not be removed.'
        : reason instanceof ApiError ? reason.message : 'We could not delete the server journey.')
      setConfirming(false)
    } finally {
      setDeleting(false)
    }
  }

  if (!tripId) return <section className="content-panel"><p className="eyebrow">Settings</p><h1>No journey saved</h1><p className="lede">Plan a hospital journey to manage its saved details.</p><Link className="button button-primary" to="/plan">Plan journey</Link></section>
  return (
    <section className="settings-page">
      <div><p className="eyebrow">Settings</p><h1>Journey settings</h1></div>
      {message && <p className="form-error" role="alert">{message}</p>}
      <section className="settings-card"><h2>Reminders</h2><p>Get an alert before your appointment when this browser supports it.</p><p className="journey-detail">A reminder is never enabled automatically.</p><ReminderControls tripId={tripId} /></section>
      <section className="settings-card"><h2>Privacy</h2><p>Delete this journey from the server and remove its saved copy on this device.</p><button ref={deleteTrigger} className="button button-danger" type="button" onClick={() => setConfirming(true)}>Delete journey</button></section>
      <Link className="text-button" to={`/trip/${encodeURIComponent(tripId)}`}>Back to journey</Link>
      <DeleteTripDialog open={confirming} onClose={() => setConfirming(false)} onConfirm={() => void removeTrip()} returnFocusRef={deleteTrigger} />
    </section>
  )
}
