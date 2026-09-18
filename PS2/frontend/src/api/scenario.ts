import { requestJson } from './client'
import type { ScenarioState } from './types'

export function getScenario() {
  return requestJson<ScenarioState>('/api/scenario')
}

export function setScenario(state: ScenarioState) {
  return requestJson<ScenarioState>('/api/scenario', { method: 'POST', body: state })
}
