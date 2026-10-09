"""Shared helpers for the test suite."""

import csv
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

EVIDENCE = os.path.join(ROOT, "evidence")
GUID_RE = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
PULL_ZONE = "vz-e81debcf-c73.b-cdn.net"
ATTRIBUTED_UPLOADER = "a89bb9dc-d09f-4475-b9ed-ae398edf928b"


def path(rel):
    return os.path.join(ROOT, rel)


def exists(rel):
    return os.path.exists(path(rel))


def load_json(rel):
    with open(path(rel), encoding="utf-8") as fh:
        return json.load(fh)


def load_csv(rel):
    with open(path(rel), encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
