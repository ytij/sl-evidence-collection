#!/usr/bin/env python3
"""RFC 3161 trusted timestamping for the evidence manifest.

Submits the SHA-256 digest of an evidence file to one or more public Time
Stamp Authorities and stores the signed token (``.tsr``) alongside the request
(``.tsq``). The token is cryptographic proof that the hashed evidence existed
at or before the TSA's signing time, and can later be verified independently
with ``openssl ts -verify``.

Usage:
    python timestamp.py                       # timestamps evidence/manifest.json
    python timestamp.py path/to/file.json
    python timestamp.py --verify              # re-check stored tokens (needs openssl)
"""

import hashlib
import json
import os
import secrets
import sys
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TARGET = os.path.join(HERE, "evidence", "manifest.json")
OUT_DIR = os.path.join(HERE, "evidence", "timestamps")

TSA_URLS = [
    "https://freetsa.org/tsr",
    "http://timestamp.digicert.com",
    "http://timestamp.sectigo.com",
]

# 2.16.840.1.101.3.4.2.1 = sha256
_SHA256_ALGID = bytes.fromhex("300d06096086480165030402010500")


def _der_len(n):
    if n < 0x80:
        return bytes([n])
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(body)]) + body


def _der(tag, content):
    return bytes([tag]) + _der_len(len(content)) + content


def _der_int(n):
    body = n.to_bytes((n.bit_length() + 7) // 8 or 1, "big")
    if body[0] & 0x80:
        body = b"\x00" + body
    return _der(0x02, body)


def build_request(digest, nonce):
    """Minimal RFC 3161 TimeStampReq with certReq=TRUE."""
    message_imprint = _der(0x30, _SHA256_ALGID + _der(0x04, digest))
    body = (
        _der_int(1)                      # version
        + message_imprint                # messageImprint
        + _der_int(nonce)                # nonce
        + _der(0x01, b"\xff")            # certReq = TRUE
    )
    return _der(0x30, body)


def _tlv(data, pos):
    tag = data[pos]
    pos += 1
    length = data[pos]
    pos += 1
    if length & 0x80:
        n = length & 0x7F
        length = int.from_bytes(data[pos:pos + n], "big")
        pos += n
    return tag, data[pos:pos + length], pos + length


def parse_status(resp):
    """Extract PKIStatus from a TimeStampResp (0=granted, 1=grantedWithMods)."""
    tag, outer, _ = _tlv(resp, 0)            # TimeStampResp SEQUENCE
    _tag, status_info, _ = _tlv(outer, 0)    # PKIStatusInfo SEQUENCE
    _tag, status, _ = _tlv(status_info, 0)   # status INTEGER
    return int.from_bytes(status, "big")


def submit(session, request_bytes):
    last = None
    for tsa in TSA_URLS:
        try:
            r = session.post(
                tsa, data=request_bytes, timeout=30,
                headers={"Content-Type": "application/timestamp-query",
                         "Accept": "application/timestamp-reply"},
            )
            if r.status_code == 200 and len(r.content) > 64 and r.content[0] == 0x30:
                status = parse_status(r.content)
                if status in (0, 1):
                    return tsa, r.content
                last = f"{tsa}: PKIStatus={status}"
            else:
                last = f"{tsa}: HTTP {r.status_code}"
        except requests.RequestException as exc:
            last = f"{tsa}: {exc.__class__.__name__}"
    raise RuntimeError(f"all TSAs failed ({last})")


def timestamp_file(target):
    with open(target, "rb") as fh:
        raw = fh.read()
    digest = hashlib.sha256(raw).digest()

    session = requests.Session()
    request_bytes = build_request(digest, secrets.randbits(64))
    tsa, token = submit(session, request_bytes)

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = os.path.basename(target).replace(".json", "")
    tsq_path = os.path.join(OUT_DIR, f"{stamp}_{name}.tsq")
    tsr_path = os.path.join(OUT_DIR, f"{stamp}_{name}.tsr")
    with open(tsq_path, "wb") as fh:
        fh.write(request_bytes)
    with open(tsr_path, "wb") as fh:
        fh.write(token)

    index_path = os.path.join(OUT_DIR, "index.json")
    index = []
    if os.path.exists(index_path):
        try:
            with open(index_path, encoding="utf-8") as fh:
                index = json.load(fh)
        except ValueError:
            index = []
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target": os.path.relpath(target, HERE).replace("\\", "/"),
        "sha256": digest.hex(),
        "tsa": tsa,
        "tsq": os.path.relpath(tsq_path, HERE).replace("\\", "/"),
        "tsr": os.path.relpath(tsr_path, HERE).replace("\\", "/"),
        "tsr_sha256": hashlib.sha256(token).hexdigest(),
    }
    index.append(record)
    with open(index_path, "w", encoding="utf-8", newline="") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)

    print(f"timestamped {record['target']}")
    print(f"  sha256 : {record['sha256']}")
    print(f"  TSA    : {tsa}")
    print(f"  token  : {record['tsr']} ({len(token)} bytes)")
    return record


def main():
    args = sys.argv[1:]
    if args and args[0] == "--verify":
        # Deferred: full verification needs a CA store; recommended via
        #   openssl ts -verify -in <tsr> -queryfile <tsq> -CAfile <tsa.pem>
        index_path = os.path.join(OUT_DIR, "index.json")
        if not os.path.exists(index_path):
            print("no timestamp index yet")
            return
        with open(index_path, encoding="utf-8") as fh:
            for rec in json.load(fh):
                print(f"{rec['target']}: {rec['sha256'][:16]} via {rec['tsa']} ({rec['created_at']})")
        return

    target = args[0] if args else DEFAULT_TARGET
    if not os.path.exists(target):
        sys.exit(f"target not found: {target}")
    timestamp_file(target)


if __name__ == "__main__":
    main()
