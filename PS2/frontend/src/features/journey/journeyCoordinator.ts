import { ApiError } from '../../api/client'
import type { OfflineBundle, RouteStatus, TripPlan } from '../../api/types'

export type JourneyApi = {
  getPlan(tripId: string): Promise<TripPlan>
  getStatus(tripId: string): Promise<RouteStatus>
  getOfflineBundle(tripId: string): Promise<OfflineBundle>
}

export type JourneyOperation = 'idle' | 'loading-plan' | 'checking-status' | 'loading-effective-plan' | 'preparing-offline'
export type StatusFreshness = 'unavailable' | 'current' | 'stale' | 'failed'

export type JourneySnapshot = {
  tripId: string
  plan: TripPlan
  status: RouteStatus | null
  receivedAt: string
  source: 'network' | 'saved'
  routeConfirmed: boolean
  statusFreshness: StatusFreshness
  generatedAt?: string
  warnings: string[]
}

export type JourneyPhase = 'loading' | 'ready' | 'refreshing' | 'degraded' | 'missing'

export type JourneyState = {
  phase: JourneyPhase
  operation: JourneyOperation
  snapshot: JourneySnapshot | null
  message: string | null
}

const initialState: JourneyState = { phase: 'loading', operation: 'loading-plan', snapshot: null, message: null }

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
    this.publish({ phase: 'loading', operation: 'loading-plan', snapshot: null, message: null })
    try {
      const plan = await this.api.getPlan(tripId)
      if (!this.isCurrent(generation, tripId)) return
      this.publish({
        phase: 'ready',
        operation: 'idle',
        snapshot: {
          tripId, plan, status: null, receivedAt: new Date().toISOString(), source: 'network', routeConfirmed: false,
          statusFreshness: 'unavailable', warnings: [],
        },
        message: 'Status not checked yet.',
      })
    } catch (error) {
      if (!this.isCurrent(generation, tripId)) return
      this.publishError(error)
    }
  }

  hydrateSaved(tripId: string, plan: TripPlan, status: RouteStatus | null, metadata: {
    generatedAt: string
    savedAt: string
    warnings: string[]
  }) {
    this.tripId = tripId
    this.publish({
      phase: 'degraded',
      operation: 'idle',
      snapshot: {
        tripId, plan, status, receivedAt: metadata.savedAt, source: 'saved', routeConfirmed: false,
        statusFreshness: status ? 'stale' : 'unavailable', generatedAt: metadata.generatedAt, warnings: metadata.warnings,
      },
      message: 'Showing written journey saved on this device. Live status is not available.',
    })
  }

  refresh() {
    if (!this.tripId) return Promise.resolve()
    if (this.pendingRefresh) return this.pendingRefresh
    this.pendingRefresh = this.refreshCurrent().finally(() => { this.pendingRefresh = null })
    return this.pendingRefresh
  }

  async prepareOffline(): Promise<OfflineBundle> {
    const tripId = this.tripId
    const generation = this.generation
    if (!tripId) throw new Error('No journey is available to save offline.')
    const previous = this.state.snapshot
    this.publish({ phase: previous ? 'refreshing' : 'loading', operation: 'preparing-offline', snapshot: previous, message: null })
    try {
      const bundle = await this.api.getOfflineBundle(tripId)
      if (!this.isCurrent(generation, tripId)) throw new Error('This journey is no longer active.')
      const plan = { ...bundle.plan, trip_id: tripId } as TripPlan
      const status = bundle.status_snapshot ?? null
      this.publish({
        phase: status?.replan_failed || plan.replan_failed ? 'degraded' : 'ready', operation: 'idle',
        snapshot: {
          tripId, plan, status, receivedAt: bundle.generated_at, source: 'network',
          routeConfirmed: Boolean(status) && !status.replan_failed && !plan.replan_failed,
          statusFreshness: status ? (status.stale ? 'stale' : 'current') : 'unavailable',
          warnings: bundle.warnings,
        },
        message: status?.replan_failed || plan.replan_failed ? 'The route could not be safely updated. Read the warnings before travelling.' : null,
      })
      return bundle
    } catch (error) {
      if (this.isCurrent(generation, tripId)) {
        this.publish({
          phase: previous ? 'degraded' : 'loading', operation: 'idle', snapshot: previous,
          message: this.messageFor(error),
        })
      }
      throw error
    }
  }

  private async refreshCurrent() {
    const tripId = this.tripId
    const generation = this.generation
    if (!tripId) return
    const previous = this.state.snapshot
    this.publish({
      phase: previous ? 'refreshing' : 'loading', operation: 'checking-status', snapshot: previous, message: null,
    })
    try {
      const status = await this.api.getStatus(tripId)
      if (!this.isCurrent(generation, tripId)) return
      try {
        this.publish({ phase: 'refreshing', operation: 'loading-effective-plan', snapshot: previous, message: null })
        const plan = await this.api.getPlan(tripId)
        if (!this.isCurrent(generation, tripId)) return
        this.publish({
          phase: 'ready', operation: 'idle',
          snapshot: {
            tripId, plan, status, receivedAt: new Date().toISOString(), source: 'network', routeConfirmed: true,
            statusFreshness: status.stale ? 'stale' : 'current', warnings: [],
          },
          message: null,
        })
      } catch (error) {
        if (!this.isCurrent(generation, tripId)) return
        if (!previous) {
          this.publishError(error)
          return
        }
        this.publish({
          phase: 'degraded', operation: 'idle',
          snapshot: {
            ...previous, status, receivedAt: new Date().toISOString(), routeConfirmed: false,
            statusFreshness: 'failed',
          },
          message: this.messageFor(error),
        })
      }
    } catch (error) {
      if (!this.isCurrent(generation, tripId)) return
      if (previous) this.publish({
        phase: 'degraded', operation: 'idle', snapshot: { ...previous, routeConfirmed: false, statusFreshness: 'failed' },
        message: this.messageFor(error),
      })
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
      this.publish({ phase: 'missing', operation: 'idle', snapshot: null, message: error.message })
      return
    }
    this.publish({ phase: 'degraded', operation: 'idle', snapshot: this.state.snapshot, message: this.messageFor(error) })
  }

  private publish(state: JourneyState) {
    this.state = state
    for (const listener of this.listeners) listener(state)
  }
}
