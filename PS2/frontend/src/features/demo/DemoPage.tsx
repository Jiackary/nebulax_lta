import { useEffect, useState } from 'react'

import { ApiError } from '../../api/client'
import { getScenario, setScenario } from '../../api/scenario'
import type { ScenarioState } from '../../api/types'

export function DemoPage() {
  const [scenario, setScenarioState] = useState<ScenarioState | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    void getScenario().then(setScenarioState).catch((reason) => setMessage(reason instanceof ApiError ? reason.message : 'We could not load demo controls.'))
  }, [])

  async function update(key: 'ewl_disruption' | 'lift_outage_outram', checked: boolean) {
    if (!scenario) return
    const next = { ...scenario, enabled: true, scenarios: { ...scenario.scenarios, [key]: checked } }
    setScenarioState(next)
    try {
      setScenarioState(await setScenario(next))
    } catch (reason) {
      setScenarioState(scenario)
      setMessage(reason instanceof ApiError ? reason.message : 'We could not change the demo scenario.')
    }
  }

  if (message && !scenario) return <section className="content-panel"><p className="eyebrow">Demo</p><h1>Demo controls unavailable</h1><p className="lede">{message}</p></section>
  if (!scenario) return <section className="content-panel" aria-live="polite"><p className="eyebrow">Demo</p><h1>Loading demo controls</h1></section>
  return (
    <section className="demo-page">
      <p className="eyebrow">Demonstration only</p><h1>Journey simulation</h1>
      <p className="form-error">These controls change the shared demo server for everyone using it. They do not describe a live transport event.</p>
      {message && <p className="form-error" role="alert">{message}</p>}
      <label className="demo-toggle"><input type="checkbox" checked={scenario.scenarios.lift_outage_outram} onChange={(event) => void update('lift_outage_outram', event.target.checked)} /> Simulate a lift outage at Outram Park</label>
      <label className="demo-toggle"><input type="checkbox" checked={scenario.scenarios.ewl_disruption} onChange={(event) => void update('ewl_disruption', event.target.checked)} /> Simulate an East-West Line disruption</label>
    </section>
  )
}
