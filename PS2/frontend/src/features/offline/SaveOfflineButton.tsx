import { useState } from 'react'

import { ApiError } from '../../api/client'
import { saveOfflineBundle } from './storage'
import { useJourney } from '../journey/useJourney'

export function SaveOfflineButton({ tripId: _tripId }: { tripId: string }) {
  const { prepareOffline } = useJourney()
  const [state, setState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [message, setMessage] = useState<string | null>(null)

  async function save() {
    setState('saving')
    setMessage(null)
    try {
      const bundle = await prepareOffline()
      await saveOfflineBundle(bundle)
      setState('saved')
      setMessage('Written journey saved on this device.')
    } catch (reason) {
      setState('error')
      setMessage(reason instanceof ApiError ? reason.message : 'We could not save written steps on this device.')
    }
  }

  return <div className="offline-save"><button className="button button-secondary" type="button" disabled={state === 'saving'} onClick={() => void save()}>{state === 'saving' ? 'Saving written steps…' : 'Save written steps offline'}</button>{message && <p className={state === 'error' ? 'form-error' : 'offline-saved'} role="status">{message}</p>}</div>
}
