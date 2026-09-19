/// <reference lib="webworker" />

import { precacheAndRoute } from 'workbox-precaching'

declare let self: ServiceWorkerGlobalScope

precacheAndRoute(self.__WB_MANIFEST)

self.addEventListener('push', (event) => {
  const payload = event.data?.json() as { title?: string; body?: string; url?: string } | undefined
  const url = payload?.url?.startsWith('/trip/') ? payload.url : '/'
  event.waitUntil(self.registration.showNotification(payload?.title ?? 'Journey update', {
    body: payload?.body ?? 'Open Nusa to check your journey.',
    data: { url },
  }))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = new URL(event.notification.data?.url ?? '/', self.location.origin)
  if (target.origin !== self.location.origin || !target.pathname.startsWith('/trip/')) target.pathname = '/'
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
    const existing = clients.find((client) => client.url === target.href)
    return existing ? existing.focus() : self.clients.openWindow(target.href)
  }))
})
