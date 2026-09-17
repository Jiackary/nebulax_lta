"""Repro for push review. Run from PS2/backend with PS2_USE_FIXTURES=1, PS2_DB, VAPID_* set."""
import asyncio, base64, collections, json, os, sys, threading, time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

sys.path.insert(0, os.getcwd())
hits = collections.Counter()
flaky_state = {"n": 0}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(n)
        hits[self.path] += 1
        if self.path == "/ok":
            code, body = 201, b""
        elif self.path == "/gone":
            code, body = 410, b"INTERNAL-SECRET-BODY"
        elif self.path == "/flaky":
            flaky_state["n"] += 1
            code, body = (500, b"oops") if flaky_state["n"] == 1 else (201, b"")
        elif self.path == "/hang":
            time.sleep(6)
            code, body = 201, b""
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


srv = ThreadingHTTPServer(("127.0.0.1", 8765), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()


def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def sub_keys():
    k = ec.generate_private_key(ec.SECP256R1())
    pub = k.public_key().public_bytes(serialization.Encoding.X962,
                                      serialization.PublicFormat.UncompressedPoint)
    return {"p256dh": b64(pub), "auth": b64(os.urandom(16))}


from app import jobs, store
from app.config import SGT

store.init()
tid = store.save_trip(datetime.now(SGT) + timedelta(hours=14), {"label": "home", "coord": [1, 2]}, {}, {})
store.save_subscription("http://127.0.0.1:8765/ok", sub_keys(), [tid])
store.save_subscription("http://127.0.0.1:8765/flaky", sub_keys(), [tid])
store.save_subscription("http://127.0.0.1:8765/gone", sub_keys(), [tid])


async def fake_check(trip):
    return {"title": "Lift out at Bedok", "body": "same", "trip_id": trip["trip_id"], "digest": "d1"}

jobs.notify.check_trip = fake_check
for i in range(3):
    r = asyncio.run(jobs.run_check("20:00", 36))
    print("run", i, r)
print("hits after 3 identical 20:00 runs:", dict(hits))
print("subs still stored:", [s["endpoint"] for s in store.subscriptions()])

# --- retention: appointment 03:30, sweeps at 03:00 next day and day after
t2 = store.save_trip(datetime(2026, 9, 20, 3, 30, tzinfo=SGT), {}, {}, {})
print("sweep@+23.5h removed", store.sweep(datetime(2026, 9, 21, 3, 0, tzinfo=SGT)),
      "trip exists:", bool(store.get_trip(t2)))
print("sweep@+47.5h removed", store.sweep(datetime(2026, 9, 22, 3, 0, tzinfo=SGT)),
      "trip exists:", bool(store.get_trip(t2)))

# --- subscribe replaces trip_ids; unsubscribe leaves the first trip
ta = store.save_trip(datetime.now(SGT) + timedelta(days=3), {"label": "home"}, {}, {})
tb = store.save_trip(datetime.now(SGT) + timedelta(days=4), {"label": "home"}, {}, {})
store.save_subscription("http://127.0.0.1:8765/phone", sub_keys(), [ta])
store.save_subscription("http://127.0.0.1:8765/phone", sub_keys(), [tb])
print(store.delete_subscription("http://127.0.0.1:8765/phone"),
      "trip A survives unsubscribe:", bool(store.get_trip(ta)))
srv.shutdown()
