/// <reference lib="webworker" />

import { createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'

declare let self: ServiceWorkerGlobalScope

precacheAndRoute(self.__WB_MANIFEST)

// Precaching the assets is not enough on its own: only '/' is a precached document, so a
// cold offline open of /trip/:id asked the network for a page that does not exist as a file
// and failed outright. That is the one journey she is most likely to make offline — she
// saved the trip precisely because she expected to lose signal. Answer every in-app
// navigation with the shell and let the router and the saved bundle take it from there.
// API requests are excluded so a failed fetch stays a failed fetch instead of becoming HTML.
registerRoute(new NavigationRoute(createHandlerBoundToURL('/index.html'), {
  denylist: [/^\/api\//],
}))

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
