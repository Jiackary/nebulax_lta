import base64, os, sys, threading, time, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from py_vapid import Vapid01
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
b64 = lambda raw: base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
v = Vapid01(); v.generate_keys()
os.environ["VAPID_PRIVATE_KEY"] = b64(v.private_key.private_numbers().private_value.to_bytes(32, "big"))
os.environ["VAPID_PUBLIC_KEY"] = "x"
db = os.environ["PS2_DB"]
if os.path.exists(db): os.remove(db)
from app.sources import base
base.Source._record = lambda *a, **k: None
from app import store
store.init()

def sub_keys():
    k = ec.generate_private_key(ec.SECP256R1())
    pub = k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return {"p256dh": b64(pub), "auth": b64(os.urandom(16))}

HITS = {}
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("content-length", 0)); self.rfile.read(n)
        HITS.setdefault(self.path, []).append(dict(self.headers))
        if self.path.startswith("/slow"): time.sleep(5)
        if self.path.startswith("/fail"):
            body = b"INTERNAL-ADMIN-PAGE-CONTENT"; self.send_response(404)
        else:
            body = b""; self.send_response(201)
        self.send_header("content-length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"
