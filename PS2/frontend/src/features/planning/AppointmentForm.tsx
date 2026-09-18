import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ApiError } from '../../api/client'
import { createTrip } from '../../api/trips'
import { singaporeDateTimeToIso, validateSingaporeDateTime } from '../../lib/singaporeTime'
import { setActiveTripId } from './activeTrip'

function futureSingaporeDateTime() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Singapore', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(Date.now() + 24 * 60 * 60 * 1000))
  const value = Object.fromEntries(parts.filter((part) => part.type !== 'literal').map((part) => [part.type, part.value]))
  return `${value.year}-${value.month}-${value.day}T${value.hour}:${value.minute}`
}

export function AppointmentForm() {
  const navigate = useNavigate()
  const [appointmentAt, setAppointmentAt] = useState(futureSingaporeDateTime)
  const [preferSheltered, setPreferSheltered] = useState(true)
  const [bufferMin, setBufferMin] = useState(15)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting) return
    const invalid = validateSingaporeDateTime(appointmentAt)
    if (invalid) {
      setError(invalid)
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      const trip = await createTrip({
        destination_id: 'SGH',
        appointment_at: singaporeDateTimeToIso(appointmentAt),
        preferences: { walking_pace: 'slow', avoid_stairs: true, prefer_sheltered: preferSheltered, buffer_min: bufferMin },
      })
      try {
        setActiveTripId(trip.trip_id)
      } catch {
        setError('Your journey is ready, but this device could not save it for next time.')
      }
      navigate(`/trip/${encodeURIComponent(trip.trip_id)}`)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : 'We could not plan your journey. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="appointment-form" onSubmit={submit} noValidate>
      <div className="form-field">
        <label htmlFor="appointment-at">Appointment date and time</label>
        <span id="appointment-help">Singapore time</span>
        <input id="appointment-at" name="appointment-at" type="datetime-local" value={appointmentAt} aria-describedby="appointment-help appointment-error" onChange={(event) => setAppointmentAt(event.target.value)} />
      </div>
      <fieldset className="form-field">
        <legend>Journey preferences</legend>
        <label className="check-row"><input type="checkbox" checked={preferSheltered} onChange={(event) => setPreferSheltered(event.target.checked)} /> Prefer more sheltered walking where available</label>
        <label>Arrival buffer
          <select value={bufferMin} onChange={(event) => setBufferMin(Number(event.target.value))}>
            <option value={0}>No extra buffer</option><option value={15}>15 minutes</option><option value={30}>30 minutes</option><option value={45}>45 minutes</option>
          </select>
        </label>
      </fieldset>
      {error && <p id="appointment-error" className="form-error" role="alert">{error}</p>}
      <button className="button button-primary" type="submit" disabled={submitting}>{submitting ? 'Planning journey…' : 'Plan journey'}</button>
    </form>
  )
}
