type OverviewLeg = {
  mode: 'rail' | 'walk'
  from: { name: string }
  to: { name: string }
  line?: { name: string } | null
}

export function RouteOverview({ legs }: { legs: OverviewLeg[] }) {
  if (legs.length === 0) return <section className="route-overview route-overview-unavailable"><strong>Route overview unavailable.</strong><span>Written steps are below.</span></section>
  const stops = [legs[0].from.name, ...legs.map((leg) => leg.to.name)]
  const detail = legs.map((leg) => leg.mode === 'rail' ? leg.line?.name ?? 'Train' : 'Walk').join(', ')
  return (
    <section className="route-overview" aria-label={`Route overview: ${stops.join(', ')}`}>
      <div className="route-overview-track" aria-hidden="true">
        {stops.map((stop, index) => <span className={`route-overview-stop ${index === 0 || index === stops.length - 1 ? 'route-overview-endpoint' : ''}`} key={`${stop}-${index}`} />)}
      </div>
      <div className="route-overview-copy"><p className="route-overview-stops">{stops.join(' · ')}</p><p className="route-overview-modes">{detail}</p></div>
      <p className="route-overview-note">Your route · schematic, not to scale</p>
    </section>
  )
}
