from app.sources import base, onemap
base.Source._record = lambda self, *a, **k: None
onemap.ONEMAP = "http://127.0.0.1:9/api"
onemap.ONEMAP_TOKEN = "fake-token-not-real"
from app import config; print('USE_FIXTURES', config.USE_FIXTURES)
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app, raise_server_exceptions=False) as c:
    r=c.get('/api/places/search', params={'q':'bedok north'}); print(r.status_code, r.headers.get('content-type'), r.text[:150])
with TestClient(app) as c:
    try: c.get('/api/places/search', params={'q':'bedok north'})
    except Exception as e: print(type(e).__mro__[:4], e)
