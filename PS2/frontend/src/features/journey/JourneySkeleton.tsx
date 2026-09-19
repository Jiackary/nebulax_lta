import { Skeleton } from '../../components/Skeleton'

export function JourneySkeleton() {
  return (
    <section className="journey-skeleton" aria-label="Journey is loading" aria-busy="true">
      <p className="eyebrow">Hospital appointment</p>
      <h1>Loading your saved route…</h1>
      {/* Approximate geometry is reserved for each region so the departure surface does not
          shift the page when it arrives. */}
      <div className="journey-skeleton-hero"><Skeleton className="skeleton-title" /><Skeleton className="skeleton-line skeleton-short" /></div>
      <div className="journey-skeleton-overview"><Skeleton className="skeleton-overview" /></div>
      <div className="journey-skeleton-steps"><Skeleton className="skeleton-line" /><Skeleton className="skeleton-line skeleton-short" /><Skeleton className="skeleton-line" /></div>
    </section>
  )
}
