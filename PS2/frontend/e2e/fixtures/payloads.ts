// Deterministic API payloads for the end-to-end suite, captured from the live backend on
// 2026-09-19 and frozen: trip id, observed-at stamps and geometry are fixed so a layout
// regression is the only thing a failure can mean.
import type { Alternatives, OfflineBundle, RouteStatus, TripPlan } from '../../src/api/types'

export const FIXTURE_TRIP_ID = 't_fixture000000000000001'

export const readyPlan: TripPlan = {
  "trip_id": "t_fixture000000000000001",
  "appointment_at": "2026-09-21T10:30:00+08:00",
  "summary": {
    "leave_by": "2026-09-21T09:22:00+08:00",
    "leave_by_label": "Leave at 09:22",
    "arrival_window": [
      "2026-09-21T10:06:32+08:00",
      "2026-09-21T10:14:48+08:00"
    ],
    "arrival_label": "arrive 10:06–10:14",
    "appointment_label": "appointment 10:30",
    "buffer_min": 15,
    "duration_min": 49,
    "range_min": [
      45,
      53
    ],
    "timing_basis": "Train ride is a scheduled 31 min, fixed by the timetable. A train every 2.5 min when she boards, so 0–2.5 min of waiting. 707 m of walking at an assumed 0.7 m/s.",
    "step_free": "yes",
    "sheltered_pct": 60,
    "walk_distance_m": 707
  },
  "legs": [
    {
      "leg_id": "l1",
      "mode": "walk",
      "from": {
        "name": "Blk 208B New Upper Changi Road",
        "coord": [
          103.93057,
          1.324782
        ]
      },
      "to": {
        "name": "Bedok",
        "coord": [
          103.929668,
          1.324168
        ],
        "station_code": "EW5",
        "exit_code": "Exit B"
      },
      "duration_min": 7,
      "distance_m": 286,
      "covered_m": 11,
      "instruction": "Walk 286 m to Bedok MRT Exit B. About 4% of it is covered.",
      "step_free": "yes",
      "surface_warnings": [],
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [
            103.930427,
            1.324853
          ],
          [
            103.930204,
            1.324491
          ],
          [
            103.930371,
            1.324412
          ],
          [
            103.930826,
            1.324501
          ],
          [
            103.930828,
            1.324332
          ],
          [
            103.929743,
            1.324185
          ]
        ]
      }
    },
    {
      "leg_id": "l2",
      "mode": "rail",
      "from": {
        "name": "Bedok",
        "coord": [
          103.930173,
          1.324011
        ],
        "station_code": "EW5",
        "exit_code": "Exit B"
      },
      "to": {
        "name": "Outram Park",
        "coord": [
          103.83914,
          1.281412
        ],
        "station_code": "EW16",
        "exit_code": "Exit 6"
      },
      "line": {
        "code": "EWL",
        "name": "East-West Line",
        "colour": "#189E4A"
      },
      "duration_min": 31,
      "headway_min": 2.5,
      "instruction": "Take the East-West Line towards Tuas Link. 11 stops.",
      "step_free": "yes",
      "access": {
        "board_at": {
          "exit_code": "Exit B",
          "status": "yes"
        },
        "alight_at": {
          "exit_code": "Exit 6",
          "status": "yes"
        }
      },
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [
            103.930173,
            1.324011
          ],
          [
            103.83914,
            1.281412
          ]
        ]
      }
    },
    {
      "leg_id": "l3",
      "mode": "walk",
      "from": {
        "name": "Outram Park",
        "coord": [
          103.838521,
          1.279012
        ],
        "station_code": "EW16",
        "exit_code": "Exit 6"
      },
      "to": {
        "name": "Singapore General Hospital, Block 3",
        "coord": [
          103.835541,
          1.279643
        ]
      },
      "duration_min": 10,
      "distance_m": 422,
      "covered_m": 411,
      "instruction": "Leave by Exit 6 and take the lift to street level. Walk 422 m to Singapore General Hospital, Block 3. Sheltered most of the way.",
      "step_free": "yes",
      "surface_warnings": [],
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [
            103.838419,
            1.27902
          ],
          [
            103.838357,
            1.278841
          ],
          [
            103.83724,
            1.279483
          ],
          [
            103.836726,
            1.27953
          ],
          [
            103.83625,
            1.2796
          ],
          [
            103.83558,
            1.279816
          ]
        ]
      }
    }
  ],
  "map": {
    "bbox": [
      103.83558,
      1.278841,
      103.930849,
      1.324853
    ],
    "geometry": {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "properties": {
            "leg_id": "l1",
            "mode": "walk"
          },
          "geometry": {
            "type": "LineString",
            "coordinates": [
              [
                103.930427,
                1.324853
              ],
              [
                103.930204,
                1.324491
              ],
              [
                103.930371,
                1.324412
              ],
              [
                103.930826,
                1.324501
              ],
              [
                103.930828,
                1.324332
              ],
              [
                103.929743,
                1.324185
              ]
            ]
          }
        },
        {
          "type": "Feature",
          "properties": {
            "leg_id": "l2",
            "mode": "rail"
          },
          "geometry": {
            "type": "LineString",
            "coordinates": [
              [
                103.930173,
                1.324011
              ],
              [
                103.83914,
                1.281412
              ]
            ]
          }
        },
        {
          "type": "Feature",
          "properties": {
            "leg_id": "l3",
            "mode": "walk"
          },
          "geometry": {
            "type": "LineString",
            "coordinates": [
              [
                103.838419,
                1.27902
              ],
              [
                103.838357,
                1.278841
              ],
              [
                103.83724,
                1.279483
              ],
              [
                103.836726,
                1.27953
              ],
              [
                103.83625,
                1.2796
              ],
              [
                103.83558,
                1.279816
              ]
            ]
          }
        }
      ]
    }
  },
  "attribution": [
    "© OpenStreetMap contributors",
    "Contains information from LTA DataMall",
    "Weather data from data.gov.sg"
  ]
}

export const okStatus: RouteStatus = {
  "trip_id": "t_fixture000000000000001",
  "overall": {
    "severity": "ok",
    "headline": "Your usual route is clear.",
    "detail": "No lift outages or delays on your way to the hospital.",
    "action": {
      "kind": "view_trip",
      "label": "See your trip"
    }
  },
  "lift_alerts": [
    {
      "station_code": "DT10",
      "station_name": "Stevens",
      "station_id": "DT10",
      "line": "DTL",
      "exit_code": null,
      "blocked_exit_refs": [],
      "lift_id": "B3L02",
      "lift_desc": "(TEL) EXIT A STREET LEVEL - PLATFORM B - PLATFORM A",
      "resolution": "unmatched",
      "parsed_exits": [
        "A"
      ],
      "line_prefix": "TEL",
      "severity": "warn",
      "label": "Lift out of service",
      "detail": "A lift at Stevens is under maintenance. We could not tell which exit it serves.",
      "affects_route": false,
      "source": "live",
      "observed_at": "2026-09-19T09:05:00+08:00",
      "stale": false
    },
    {
      "station_code": "NE14",
      "station_name": "Hougang",
      "station_id": "NE14",
      "line": "NEL",
      "exit_code": "Exit A",
      "blocked_exit_refs": [
        "A"
      ],
      "lift_id": "B1 L01",
      "lift_desc": "Exit A Street level - Concourse",
      "resolution": "matched_exit",
      "parsed_exits": [
        "A"
      ],
      "line_prefix": null,
      "severity": "warn",
      "label": "Lift out of service",
      "detail": "Exit A's lift is under maintenance.",
      "affects_route": false,
      "source": "live",
      "observed_at": "2026-09-19T09:05:00+08:00",
      "stale": false
    }
  ],
  "disruption": null,
  "crowd": [
    {
      "station_code": "EW16",
      "station_name": "Outram Park",
      "level": "low",
      "label": "Not crowded",
      "severity": "ok",
      "window": [
        "2026-09-19T13:10:00+08:00",
        "2026-09-19T13:20:00+08:00"
      ],
      "source": "live",
      "stale": false,
      "observed_at": "2026-09-19T09:05:00+08:00"
    },
    {
      "station_code": "EW5",
      "station_name": "Bedok",
      "level": "low",
      "label": "Not crowded",
      "severity": "ok",
      "window": [
        "2026-09-19T13:10:00+08:00",
        "2026-09-19T13:20:00+08:00"
      ],
      "source": "live",
      "stale": false,
      "observed_at": "2026-09-19T09:05:00+08:00"
    }
  ],
  "weather": {
    "rain_expected": false,
    "areas": [
      {
        "name": "Bedok",
        "for": "home",
        "distance_km": 0.84,
        "forecast": "Cloudy"
      },
      {
        "name": "City",
        "for": "hospital",
        "distance_km": 1.66,
        "forecast": "Cloudy"
      }
    ],
    "label": "No rain forecast for Bedok or City in the next 2 hours",
    "severity": "ok",
    "affects_route": false,
    "source": "live",
    "stale": false,
    "observed_at": "2026-09-19T09:05:00+08:00"
  },
  "checks": {
    "last_checked_at": "2026-09-19T09:05:00+08:00",
    "next_check_at": "2026-09-19T09:20:00+08:00",
    "label": "Checked 09:05. We'll check again at 09:20."
  },
  "rerouted": false,
  "replan_failed": false,
  "stale": false,
  "observed_at": "2026-09-19T09:05:00+08:00"
}

export const alternatives: Alternatives = {
  "trip_id": "t_fixture000000000000001",
  "disruption": null,
  "original": {
    "label": "Your usual route",
    "duration_min": 49,
    "arrival_at": "2026-09-21T10:14:48+08:00",
    "viable": true,
    "step_free": "yes",
    "note": "Running normally."
  },
  "options": [
    {
      "option_id": "bus_wab",
      "label": "Bus 2 from Bedok Stn Exit A",
      "why": "One bus, no changes, from Bedok Stn Exit A.",
      "delta_min": 11,
      "step_free": "unknown",
      "severity": "info",
      "timing_basis": "Journey time from OneMap's public-transport route for this departure; arrival and load read live from LTA.",
      "legs": [],
      "rank": 1,
      "mode": "bus",
      "duration_min": 60,
      "bus": {
        "service_no": "2",
        "board_stop": "Bedok Stn Exit A",
        "board_stop_code": "84039",
        "alight_stop": "Bef Neil Rd",
        "alight_stop_code": "10011",
        "stops": 35,
        "distance_km": 12.3,
        "walk_min": 13,
        "ride_min": 47,
        "eta_min": null,
        "eta_is_scheduled": null,
        "load": null,
        "load_label": null,
        "wheelchair_accessible": null,
        "not_running": false,
        "first_bus": "0557",
        "last_bus": "0018",
        "observed_at": null,
        "stale": null
      }
    },
    {
      "option_id": "taxi_bfa",
      "label": "Barrier-free taxi from New Upp Changi Rd outside Bedok MRT station (towards City)",
      "why": "The nearest barrier-free taxi stand to Bedok, 82 m away.",
      "delta_min": null,
      "step_free": "yes",
      "severity": "info",
      "timing_basis": "No fare or arrival estimate: we cannot verify either.",
      "legs": [],
      "rank": 2,
      "mode": "taxi",
      "taxi_stand": {
        "name": "New Upp Changi Rd outside Bedok MRT station (towards City)",
        "coord": [
          103.92953,
          1.323646586
        ],
        "distance_m": 82,
        "barrier_free": true,
        "fare_estimate": null,
        "anchor": "EW5"
      }
    }
  ],
  "not_offered": [
    {
      "label": "Free bridging bus",
      "why_not": "These run crowded with standing room only, which is the wrong trade for a slow walker who needs a seat."
    }
  ]
}

export const offlineBundle: OfflineBundle = {
  "trip_id": "t_fixture000000000000001",
  "generated_at": "2026-09-19T09:05:00+08:00",
  "plan": {
    "trip_id": "t_fixture000000000000001",
    "appointment_at": "2026-09-21T10:30:00+08:00",
    "summary": {
      "leave_by": "2026-09-21T09:22:00+08:00",
      "leave_by_label": "Leave at 09:22",
      "arrival_window": [
        "2026-09-21T10:06:32+08:00",
        "2026-09-21T10:14:48+08:00"
      ],
      "arrival_label": "arrive 10:06–10:14",
      "appointment_label": "appointment 10:30",
      "buffer_min": 15,
      "duration_min": 49,
      "range_min": [
        45,
        53
      ],
      "timing_basis": "Train ride is a scheduled 31 min, fixed by the timetable. A train every 2.5 min when she boards, so 0–2.5 min of waiting. 707 m of walking at an assumed 0.7 m/s.",
      "step_free": "yes",
      "sheltered_pct": 60,
      "walk_distance_m": 707
    },
    "legs": [
      {
        "leg_id": "l1",
        "mode": "walk",
        "from": {
          "name": "Blk 208B New Upper Changi Road",
          "coord": [
            103.93057,
            1.324782
          ]
        },
        "to": {
          "name": "Bedok",
          "coord": [
            103.929668,
            1.324168
          ],
          "station_code": "EW5",
          "exit_code": "Exit B"
        },
        "duration_min": 7,
        "distance_m": 286,
        "covered_m": 11,
        "instruction": "Walk 286 m to Bedok MRT Exit B. About 4% of it is covered.",
        "step_free": "yes",
        "surface_warnings": [],
        "geometry": {
          "type": "LineString",
          "coordinates": [
            [
              103.930427,
              1.324853
            ],
            [
              103.930204,
              1.324491
            ],
            [
              103.930371,
              1.324412
            ],
            [
              103.930826,
              1.324501
            ],
            [
              103.930828,
              1.324332
            ],
            [
              103.929743,
              1.324185
            ]
          ]
        }
      },
      {
        "leg_id": "l2",
        "mode": "rail",
        "from": {
          "name": "Bedok",
          "coord": [
            103.930173,
            1.324011
          ],
          "station_code": "EW5",
          "exit_code": "Exit B"
        },
        "to": {
          "name": "Outram Park",
          "coord": [
            103.83914,
            1.281412
          ],
          "station_code": "EW16",
          "exit_code": "Exit 6"
        },
        "line": {
          "code": "EWL",
          "name": "East-West Line",
          "colour": "#189E4A"
        },
        "duration_min": 31,
        "headway_min": 2.5,
        "instruction": "Take the East-West Line towards Tuas Link. 11 stops.",
        "step_free": "yes",
        "access": {
          "board_at": {
            "exit_code": "Exit B",
            "status": "yes"
          },
          "alight_at": {
            "exit_code": "Exit 6",
            "status": "yes"
          }
        },
        "geometry": {
          "type": "LineString",
          "coordinates": [
            [
              103.930173,
              1.324011
            ],
            [
              103.83914,
              1.281412
            ]
          ]
        }
      },
      {
        "leg_id": "l3",
        "mode": "walk",
        "from": {
          "name": "Outram Park",
          "coord": [
            103.838521,
            1.279012
          ],
          "station_code": "EW16",
          "exit_code": "Exit 6"
        },
        "to": {
          "name": "Singapore General Hospital, Block 3",
          "coord": [
            103.835541,
            1.279643
          ]
        },
        "duration_min": 10,
        "distance_m": 422,
        "covered_m": 411,
        "instruction": "Leave by Exit 6 and take the lift to street level. Walk 422 m to Singapore General Hospital, Block 3. Sheltered most of the way.",
        "step_free": "yes",
        "surface_warnings": [],
        "geometry": {
          "type": "LineString",
          "coordinates": [
            [
              103.838419,
              1.27902
            ],
            [
              103.838357,
              1.278841
            ],
            [
              103.83724,
              1.279483
            ],
            [
              103.836726,
              1.27953
            ],
            [
              103.83625,
              1.2796
            ],
            [
              103.83558,
              1.279816
            ]
          ]
        }
      }
    ],
    "map": {
      "bbox": [
        103.83558,
        1.278841,
        103.930849,
        1.324853
      ],
      "geometry": {
        "type": "FeatureCollection",
        "features": [
          {
            "type": "Feature",
            "properties": {
              "leg_id": "l1",
              "mode": "walk"
            },
            "geometry": {
              "type": "LineString",
              "coordinates": [
                [
                  103.930427,
                  1.324853
                ],
                [
                  103.930204,
                  1.324491
                ],
                [
                  103.930371,
                  1.324412
                ],
                [
                  103.930826,
                  1.324501
                ],
                [
                  103.930828,
                  1.324332
                ],
                [
                  103.929743,
                  1.324185
                ]
              ]
            }
          },
          {
            "type": "Feature",
            "properties": {
              "leg_id": "l2",
              "mode": "rail"
            },
            "geometry": {
              "type": "LineString",
              "coordinates": [
                [
                  103.930173,
                  1.324011
                ],
                [
                  103.83914,
                  1.281412
                ]
              ]
            }
          },
          {
            "type": "Feature",
            "properties": {
              "leg_id": "l3",
              "mode": "walk"
            },
            "geometry": {
              "type": "LineString",
              "coordinates": [
                [
                  103.838419,
                  1.27902
                ],
                [
                  103.838357,
                  1.278841
                ],
                [
                  103.83724,
                  1.279483
                ],
                [
                  103.836726,
                  1.27953
                ],
                [
                  103.83625,
                  1.2796
                ],
                [
                  103.83558,
                  1.279816
                ]
              ]
            }
          }
        ]
      }
    },
    "attribution": [
      "© OpenStreetMap contributors",
      "Contains information from LTA DataMall",
      "Weather data from data.gov.sg"
    ]
  },
  "status_snapshot": {
    "trip_id": "t_fixture000000000000001",
    "overall": {
      "severity": "ok",
      "headline": "Your usual route is clear.",
      "detail": "No lift outages or delays on your way to the hospital.",
      "action": {
        "kind": "view_trip",
        "label": "See your trip"
      }
    },
    "lift_alerts": [
      {
        "station_code": "DT10",
        "station_name": "Stevens",
        "station_id": "DT10",
        "line": "DTL",
        "exit_code": null,
        "blocked_exit_refs": [],
        "lift_id": "B3L02",
        "lift_desc": "(TEL) EXIT A STREET LEVEL - PLATFORM B - PLATFORM A",
        "resolution": "unmatched",
        "parsed_exits": [
          "A"
        ],
        "line_prefix": "TEL",
        "severity": "warn",
        "label": "Lift out of service",
        "detail": "A lift at Stevens is under maintenance. We could not tell which exit it serves.",
        "affects_route": false,
        "source": "live",
        "observed_at": "2026-09-19T09:05:00+08:00",
        "stale": false
      },
      {
        "station_code": "NE14",
        "station_name": "Hougang",
        "station_id": "NE14",
        "line": "NEL",
        "exit_code": "Exit A",
        "blocked_exit_refs": [
          "A"
        ],
        "lift_id": "B1 L01",
        "lift_desc": "Exit A Street level - Concourse",
        "resolution": "matched_exit",
        "parsed_exits": [
          "A"
        ],
        "line_prefix": null,
        "severity": "warn",
        "label": "Lift out of service",
        "detail": "Exit A's lift is under maintenance.",
        "affects_route": false,
        "source": "live",
        "observed_at": "2026-09-19T09:05:00+08:00",
        "stale": false
      }
    ],
    "disruption": null,
    "crowd": [
      {
        "station_code": "EW16",
        "station_name": "Outram Park",
        "level": "low",
        "label": "Not crowded",
        "severity": "ok",
        "window": [
          "2026-09-19T13:10:00+08:00",
          "2026-09-19T13:20:00+08:00"
        ],
        "source": "live",
        "stale": false,
        "observed_at": "2026-09-19T09:05:00+08:00"
      },
      {
        "station_code": "EW5",
        "station_name": "Bedok",
        "level": "low",
        "label": "Not crowded",
        "severity": "ok",
        "window": [
          "2026-09-19T13:10:00+08:00",
          "2026-09-19T13:20:00+08:00"
        ],
        "source": "live",
        "stale": false,
        "observed_at": "2026-09-19T09:05:00+08:00"
      }
    ],
    "weather": {
      "rain_expected": false,
      "areas": [
        {
          "name": "Bedok",
          "for": "home",
          "distance_km": 0.84,
          "forecast": "Cloudy"
        },
        {
          "name": "City",
          "for": "hospital",
          "distance_km": 1.66,
          "forecast": "Cloudy"
        }
      ],
      "label": "No rain forecast for Bedok or City in the next 2 hours",
      "severity": "ok",
      "affects_route": false,
      "source": "live",
      "stale": false,
      "observed_at": "2026-09-19T09:05:00+08:00"
    },
    "checks": {
      "last_checked_at": "2026-09-19T09:05:00+08:00",
      "next_check_at": "2026-09-19T09:20:00+08:00",
      "label": "Checked 09:05. We'll check again at 09:20."
    },
    "rerouted": false,
    "replan_failed": false,
    "stale": false,
    "observed_at": "2026-09-19T09:05:00+08:00"
  },
  "steps_plain": [
    "Walk 286 m to Bedok MRT Exit B. About 4% of it is covered.",
    "Take the East-West Line towards Tuas Link. 11 stops, about 31 minutes.",
    "Leave by Exit 6 and take the lift to street level. Walk 422 m to Singapore General Hospital, Block 3. Sheltered most of the way."
  ],
  "tiles": {
    "style_url": null,
    "tile_pack_url": null,
    "attribution": "© OpenStreetMap contributors",
    "zoom_range": [
      13,
      17
    ],
    "unavailable_reason": "No tile provider whose terms permit offline caching has been chosen. The offline screen shows written steps."
  },
  "warnings": [],
  "offline_notice": "No signal: plan as of 13:37. Times may have changed.",
  "attribution": [
    "© OpenStreetMap contributors",
    "Contains information from LTA DataMall",
    "Weather data from data.gov.sg"
  ]
}
