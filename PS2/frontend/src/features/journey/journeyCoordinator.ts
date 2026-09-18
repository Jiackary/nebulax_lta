import { ApiError } from '../../api/client'
import type { OfflineBundle, RouteStatus, TripPlan } from '../../api/types'

export type JourneyApi = {
  getPlan(tripId: string): Promise<TripPlan>
  getStatus(tripId: string): Promise<RouteStatus>
  getOfflineBundle(tripId: string): Promise<OfflineBundle>
}

export type JourneySnapshot = {
  tripId: string
  plan: TripPlan
  status: RouteStatus | null
  receivedAt: string
  source: 'network' | 'saved'
  routeConfirmed: boolean
}

export type JourneyPhase = 'loading' | 'ready' | 'refreshing' | 'degraded' | 'missing'

export type JourneyState = {
  phase: JourneyPhase
  snapshot: JourneySnapshot | null
  message: string | null
}

const initialState: JourneyState = { phase: 'loading', snapshot: null, message: null }

export class JourneyCoordinator {
  private readonly api: JourneyApi
  private tripId: string | null = null
  private generation = 0
  private pendingRefresh: Promise<void> | null = null
  private listeners = new Set<(state: JourneyState) => void>()
  state: JourneyState = initialState

  constructor(api: JourneyApi) {
    this.api = api
  }

  subscribe(listener: (state: JourneyState) => void) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  dispose() {
    this.generation += 1
    this.pendingRefresh = null
    this.listeners.clear()
  }

  async initialize(tripId: string) {
    const generation = ++this.generation
    this.tripId = tripId
    this.publish({ phase: 'loading', snapshot: null, message: null })
    try {
      const plan = await this.api.getPlan(tripId)
      if (!this.isCurrent(generation, tripId)) return
      this.publish({
        phase: 'ready',
        snapshot: { tripId, plan, status: null, receivedAt: new Date().toISOString(), source: 'network', routeConfirmed: false },
        message: 'Status not checked yet.',
      })
    } catch (error) {
      if (!this.isCurrent(generation, tripId)) return
      this.publishError(error)
    }
  }

  hydrateSaved(tripId: string, plan: TripPlan, status: RouteStatus | null) {
    this.tripId = tripId
    this.publish({
      phase: 'degraded',
      snapshot: { tripId, plan, status, receivedAt: new Date().toISOString(), source: 'saved', routeConfirmed: false },
      message: 'Showing written journey saved on this device. Live status is not available.',
    })
  }

  refresh() {
    if (!this.tripId) return Promise.resolve()
    if (this.pendingRefresh) return this.pendingRefresh
    this.pendingRefresh = this.refreshCurrent().finally(() => { this.pendingRefresh = null })
    return this.pendingRefresh
  }

  private async refreshCurrent() {
    const tripId = this.tripId
    const generation = this.generation
    if (!tripId) return
    const previous = this.state.snapshot
    this.publish({ phase: previous ? 'refreshing' : 'loading', snapshot: previous, message: null })
    try {
      const status = await this.api.getStatus(tripId)
      if (!this.isCurrent(generation, tripId)) return
      try {
        const plan = await this.api.getPlan(tripId)
        if (!this.isCurrent(generation, tripId)) return
        this.publish({
          phase: 'ready',
          snapshot: { tripId, plan, status, receivedAt: new Date().toISOString(), source: 'network', routeConfirmed: true },
          message: null,
        })
      } catch (error) {
        if (!this.isCurrent(generation, tripId)) return
        if (!previous) {
          this.publishError(error)
          return
        }
        this.publish({
          phase: 'degraded',
          snapshot: { ...previous, status, receivedAt: new Date().toISOString(), routeConfirmed: false },
          message: this.messageFor(error),
        })
      }
    } catch (error) {
      if (!this.isCurrent(generation, tripId)) return
      if (previous) this.publish({ phase: 'degraded', snapshot: previous, message: this.messageFor(error) })
      else this.publishError(error)
    }
  }

  private isCurrent(generation: number, tripId: string) {
    return generation === this.generation && tripId === this.tripId
  }

  private messageFor(error: unknown) {
    return error instanceof ApiError ? error.message : 'We could not update this journey. Please try again.'
  }

  private publishError(error: unknown) {
    if (error instanceof ApiError && error.code === 'TRIP_NOT_FOUND') {
      this.publish({ phase: 'missing', snapshot: null, message: error.message })
      return
    }
    this.publish({ phase: 'degraded', snapshot: this.state.snapshot, message: this.messageFor(error) })
  }

  private publish(state: JourneyState) {
    this.state = state
    for (const listener of this.listeners) listener(state)
  }
}
