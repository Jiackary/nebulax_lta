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

class ServiceWorkerUnavailableError extends Error {}

const READY_TIMEOUT_MS = 5000

// navigator.serviceWorker.ready never rejects: when no worker takes control it stays pending
// forever, leaving the button stuck on 'Enabling reminders…'. Private windows, blocked site
// storage and locked-down browsers all land there. Race it so the failure is reportable.
function serviceWorkerReady() {
  let timer: ReturnType<typeof setTimeout> | undefined
  return Promise.race([
    navigator.serviceWorker.ready,
    new Promise<never>((_, reject) => {
      timer = setTimeout(() => reject(new ServiceWorkerUnavailableError()), READY_TIMEOUT_MS)
    }),
  ]).finally(() => clearTimeout(timer))
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
      const registration = await serviceWorkerReady()
      const { public_key } = await getPushKey()
      const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: base64UrlToBytes(public_key) })
      const json = subscription.toJSON()
      if (!json.endpoint || !json.keys?.auth || !json.keys.p256dh) throw new Error('The browser did not create a complete push subscription.')
      await savePushSubscription({ endpoint: json.endpoint, keys: { auth: json.keys.auth, p256dh: json.keys.p256dh } }, tripId)
      setState('enabled')
      setMessage('Journey reminders are enabled for this device.')
    } catch (reason) {
      setState('idle')
      if (reason instanceof ServiceWorkerUnavailableError) setMessage('This browser did not start the background service reminders need. Close and reopen the app, then try again.')
      else setMessage(reason instanceof ApiError ? reason.message : 'We could not enable reminders on this device.')
    }
  }

  if (state === 'enabled') return <p className="offline-saved" role="status">{message}</p>
  return <div className="reminder-controls"><button className="button button-secondary" type="button" disabled={state === 'enabling'} onClick={() => void enable()}>{state === 'enabling' ? 'Enabling reminders…' : 'Enable reminders'}</button>{message && <p className="journey-detail" role="status">{message}</p>}</div>
}
