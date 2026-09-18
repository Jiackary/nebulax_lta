import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { ApiError } from '../../api/client'
import { getAlternatives } from '../../api/trips'
import type { Alternatives } from '../../api/types'
import { OptionCard } from './OptionCard'

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
  if (!alternatives) return <section className="content-panel" aria-live="polite"><p className="eyebrow">Other ways to travel</p><h1>Checking your options</h1></section>

  return (
    <section className="options-page">
      <div className="section-heading"><div><p className="eyebrow">Other ways to travel</p><h1>Compare your options</h1></div><Link className="text-button" to={`/trip/${encodeURIComponent(tripId)}`}>Back to journey</Link></div>
      <p className="lede">These are information only. Choosing an option does not change your saved journey.</p>
      <section className="original-option"><strong>Usual route</strong><span>{alternatives.original.viable ? 'Still available' : 'May not be available'} · {alternatives.original.note}</span></section>
      <div className="options-list">{alternatives.options.map((option) => <OptionCard key={option.option_id} option={option} />)}</div>
      {alternatives.not_offered.length > 0 && <section className="not-offered"><h2>Not offered</h2>{alternatives.not_offered.map((item) => <p key={item.label}><strong>{item.label}:</strong> {item.why_not}</p>)}</section>}
    </section>
  )
}
