import type { components } from './generated'

type Schema = components['schemas']

export type TripRequest = Schema['TripRequest']
export type TripPlan = Schema['TripPlan']
export type RouteStatus = Schema['RouteStatus']
export type Alternatives = Schema['Alternatives']
export type OfflineBundle = Schema['OfflineBundle']
export type Attribution = Schema['Attribution']
export type ScenarioState = Schema['ScenarioState']
export type PushKey = Schema['PushKey']
