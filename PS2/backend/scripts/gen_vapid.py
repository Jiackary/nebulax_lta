#!/usr/bin/env python3
"""Generate a Web Push VAPID key pair (D4).

    python scripts/gen_vapid.py >> ../.env

The public key is served to the browser; the private key must stay in .env,
which is gitignored. A committed credential caps the score (PS2_README.md:L290).
"""
import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid01


def main() -> None:
    v = Vapid01()
    v.generate_keys()
    b64 = lambda raw: base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    private = v.private_key.private_numbers().private_value.to_bytes(32, "big")
    public = v.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint)
    print(f"VAPID_PUBLIC_KEY={b64(public)}")
    print(f"VAPID_PRIVATE_KEY={b64(private)}")
    print("VAPID_CLAIM_EMAIL=mailto:you@example.org")


if __name__ == "__main__":
    main()
