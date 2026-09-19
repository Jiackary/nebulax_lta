import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { ApiError } from '../../api/client'
import { getAlternatives } from '../../api/trips'
import type { Alternatives } from '../../api/types'
import { OptionCard } from './OptionCard'
import { Skeleton } from '../../components/Skeleton'

export function AlternativesPage({ tripId }: { tripId: string }) {
  const [alternatives, setAlternatives] = useState<Alternatives | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void getAlternatives(tripId).then((result) => { if (active) setAlternatives(result) }).catch((reason) => {
      if (active) setError(reason instanceof ApiError ? reason.message : 'We could not load your options.')
    })
    return () => { active = false }
  }, [tripId])

  if (error) return <section className="content-panel"><p className="eyebrow">Other ways to travel</p><h1>Options are unavailable</h1><p className="lede">{error}</p><Link className="button button-primary" to={`/trip/${encodeURIComponent(tripId)}`}>Back to journey</Link></section>
  if (!alternatives) return (
    <section className="options-page" aria-live="polite" aria-busy="true">
      <div><p className="eyebrow">Other ways to travel</p><h1>Checking other ways to travel…</h1><p className="lede">Looking for available alternatives.</p></div>
      {[0, 1].map((index) => <article className="option-card option-skeleton" aria-label="Travel option is loading" key={index}><Skeleton className="skeleton-line skeleton-short" /><Skeleton className="skeleton-title" /><Skeleton className="skeleton-line" /></article>)}
    </section>
  )

  return (
    <section className="options-page">
      <div><p className="eyebrow">Other ways to travel</p><h1>Compare your options</h1></div>
      <p className="lede">These are information only. Choosing an option does not change your saved journey.</p>
      <section className="original-option"><strong>Usual route</strong><span>{alternatives.original.viable ? 'Still available' : 'May not be available'} · {alternatives.original.note}</span></section>
      <div className="options-list">{alternatives.options.map((option) => <OptionCard key={option.option_id} option={option} />)}</div>
      {alternatives.not_offered.length > 0 && <section className="not-offered"><h2>Not offered</h2>{alternatives.not_offered.map((item) => <p key={item.label}><strong>{item.label}:</strong> {item.why_not}</p>)}</section>}
    </section>
  )
}
