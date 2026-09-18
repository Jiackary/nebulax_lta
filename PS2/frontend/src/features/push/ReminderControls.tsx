import { useState } from 'react'

import { ApiError } from '../../api/client'
import { getPushKey, savePushSubscription } from '../../api/push'

function base64UrlToBytes(value: string) {
  const padded = value.padEnd(value.length + (4 - value.length % 4) % 4, '=')
  const binary = atob(padded.replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(binary, (character) => character.charCodeAt(0))
}

function supported() {
  return 'Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window
}

export function ReminderControls({ tripId }: { tripId: string }) {
  const [state, setState] = useState<'idle' | 'enabling' | 'enabled' | 'unavailable'>('idle')
  const [message, setMessage] = useState<string | null>(null)

  async function enable() {
    if (!supported()) {
      setState('unavailable')
      setMessage('This browser does not support journey reminders.')
      return
    }
    setState('enabling')
    setMessage(null)
    try {
      const registration = await navigator.serviceWorker.ready
      const { public_key } = await getPushKey()
      const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: base64UrlToBytes(public_key) })
      const json = subscription.toJSON()
      if (!json.endpoint || !json.keys?.auth || !json.keys.p256dh) throw new Error('The browser did not create a complete push subscription.')
      await savePushSubscription({ endpoint: json.endpoint, keys: { auth: json.keys.auth, p256dh: json.keys.p256dh } }, tripId)
      setState('enabled')
      setMessage('Journey reminders are enabled for this device.')
    } catch (reason) {
      setState('idle')
      setMessage(reason instanceof ApiError ? reason.message : 'We could not enable reminders on this device.')
    }
  }

  if (state === 'enabled') return <p className="offline-saved" role="status">{message}</p>
  return <div className="reminder-controls"><button className="button button-secondary" type="button" disabled={state === 'enabling'} onClick={() => void enable()}>{state === 'enabling' ? 'Enabling reminders…' : 'Enable reminders'}</button>{message && <p className="journey-detail" role="status">{message}</p>}</div>
}
