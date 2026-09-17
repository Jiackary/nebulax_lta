from app.sources import base
base.Source._record = lambda self, *a, **k: None
from fastapi.testclient import TestClient
from app.main import app
import json
with TestClient(app) as c:
    for b in [{"origin":{"coord":[]}}, {"origin":{"coord":[103.93]}}, {"origin":{"coord":[103.93057,1.324782,5]}}, {"preferences":{"buffer_min":1e12}}]:
        b["appointment_at"]="2026-09-21T10:30:00+08:00"
        try: c.post('/api/trips', json=b)
        except Exception as e: print(b, type(e).__name__, e)
    r=c.post('/api/trips', json={"appointment_at":"2026-09-21T10:30:00+08:00","preferences":{"walking_pace":"sprint"}})
    print('POST has sprint', 'sprint' in r.text)
    tid=r.json()['trip_id']
    for p in [f'/api/trips/{tid}', f'/api/trips/{tid}/offline', f'/api/trips/{tid}/status']:
        x=c.get(p); print(p, x.status_code, 'sprint' in x.text)
    from app import store
    t=store.get_trip(tid); print({k:v for k,v in t.items() if k!='plan'})
    for tid2 in []: pass
