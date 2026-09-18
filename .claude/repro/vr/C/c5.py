import json
from app.sources import base
base.Source._record = lambda self, *a, **k: None
from fastapi.testclient import TestClient
from app.main import app
import pydantic, fastapi, starlette
print('versions', pydantic.VERSION, fastapi.__version__, starlette.__version__)
def body(**kw):
    b={"appointment_at":"2026-09-21T10:30:00+08:00"}
    b.update(kw); return b
with TestClient(app, raise_server_exceptions=False) as c:
    def post(label, b, raw=None):
        if raw is not None:
            r=c.post('/api/trips', content=raw, headers={'content-type':'application/json'})
        else:
            r=c.post('/api/trips', json=b)
        ct=r.headers.get('content-type')
        try: j=r.json()
        except Exception: j=r.text[:80]
        if isinstance(j,dict) and 'summary' in j:
            j={'trip_id':j['trip_id'],'appt':j['appointment_at'],'leave':j['summary']['leave_by_label'],'buffer':j['summary']['buffer_min']}
        print(label, r.status_code, ct, str(j)[:200])
        return r
    post('coord []', body(origin={"coord":[]}))
    post('coord [103.93]', body(origin={"coord":[103.93]}))
    post('coord xyz', body(origin={"coord":[103.93057,1.324782,5]}))
    post('coord NaN', None, raw='{"appointment_at":"2026-09-21T10:30:00+08:00","origin":{"coord":[NaN,NaN]}}')
    post('buffer -120', body(preferences={"buffer_min":-120}))
    post('buffer 1e12', body(preferences={"buffer_min":1e12}))
    post('buffer 1000000000000 int', body(preferences={"buffer_min":1000000000000}))
    r=post('year 2001', body(appointment_at="2001-01-01T10:30:00+08:00"))
    r=post('year 9999', body(appointment_at="9999-12-31T10:30:00+08:00"))
    r=post('date only', body(appointment_at="2026-09-21"))
    r=post('sprint', body(preferences={"walking_pace":"sprint"}))
    tid=r.json().get('trip_id')
    g=c.get(f'/api/trips/{tid}')
    print('stored pace sprint?', 'sprint' in json.dumps(g.json()), g.json()['summary']['timing_basis'])
    import sqlite3
    # year 2001/9999 stored?
    from app import store
    # C7
    for m,u in [('get','/api/nope'),('put','/api/trips'),('get','/api/trips/xyz'),('delete','/api/destinations')]:
        r=getattr(c,m)(u); print('C7',m,u,r.status_code,r.headers.get('content-type'),r.text[:120])
    r=c.get('/api/trips/doesnotexist/status'); print('status unknown', r.status_code, r.headers.get('content-type'), r.text[:120])
