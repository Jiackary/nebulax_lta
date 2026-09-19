import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ApiError } from '../../api/client'
import { createTrip } from '../../api/trips'
import { formatSingaporeDateTime, singaporeDateTimeToIso, validateSingaporeDateTime } from '../../lib/singaporeTime'
import { AsyncFeedback } from '../../components/AsyncFeedback'
import { setActiveTripId } from './activeTrip'

export function AppointmentForm() {
  const navigate = useNavigate()
  // No default. Tomorrow at the current minute is not an appointment anyone has; pre-filling
  // it invites a journey planned for a time the reader never chose.
  const [appointmentAt, setAppointmentAt] = useState('')
  const [preferSheltered, setPreferSheltered] = useState(true)
  const [bufferMin, setBufferMin] = useState(15)
  // The field error describes the input; the form error describes the request. A failed
  // network call must not mark a perfectly valid date as invalid.
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const preview = appointmentAt && !validateSingaporeDateTime(appointmentAt)
    ? formatSingaporeDateTime(singaporeDateTimeToIso(appointmentAt))
    : null

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting) return
    const invalid = validateSingaporeDateTime(appointmentAt)
    if (invalid) {
      setFieldError(appointmentAt ? invalid : 'Choose the date and time of your appointment.')
      setFormError(null)
      return
    }
    setFieldError(null)
    setFormError(null)
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
        setFormError('Your journey is ready, but this device could not save it for next time.')
      }
      navigate(`/trip/${encodeURIComponent(trip.trip_id)}`)
    } catch (reason) {
      setFormError(reason instanceof ApiError ? reason.message : 'We could not plan your journey. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="appointment-form" onSubmit={submit} noValidate>
      <div className="form-field">
        <label htmlFor="appointment-at">Appointment date and time</label>
        <span className="field-helper" id="appointment-help">Singapore time. Choose the time printed on your appointment letter.</span>
        <input
          id="appointment-at"
          name="appointment-at"
          type="datetime-local"
          value={appointmentAt}
          required
          aria-describedby={fieldError ? 'appointment-help appointment-field-error' : 'appointment-help'}
          aria-invalid={Boolean(fieldError)}
          disabled={submitting}
          onChange={(event) => { setAppointmentAt(event.target.value); setFieldError(null) }}
        />
        {preview && <span className="field-helper">{preview}</span>}
        {fieldError && <p id="appointment-field-error" className="form-error" role="alert">{fieldError}</p>}
      </div>
      <fieldset className="form-field" disabled={submitting}>
        <legend>Journey preferences</legend>
        <label className="check-row"><input type="checkbox" checked={preferSheltered} onChange={(event) => setPreferSheltered(event.target.checked)} /> Prefer more sheltered walking where available</label>
        <label>Arrive early by
          <span className="field-helper">Extra time before your appointment.</span>
          <select value={bufferMin} onChange={(event) => setBufferMin(Number(event.target.value))}>
            <option value={0}>No extra buffer</option><option value={15}>15 minutes</option><option value={30}>30 minutes</option><option value={45}>45 minutes</option>
          </select>
        </label>
      </fieldset>
      {formError && <p className="form-error" role="alert">{formError}</p>}
      <AsyncFeedback operation={submitting ? 'creating-trip' : 'idle'} label="Preparing your journey…" />
      <button className="button button-primary" type="submit" disabled={submitting}>{submitting ? 'Planning journey…' : 'Plan journey'}</button>
    </form>
  )
}
