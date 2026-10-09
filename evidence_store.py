#!/usr/bin/env python3
"""Append-only evidence store with a SHA-256 manifest.

Persists the raw rows returned by each backend/API call into ``evidence/`` so
the data is preserved in the repository (git history then provides an immutable
record of every prior snapshot). Every write records the source URL, row count,
timestamp and content hash in ``evidence/manifest.json`` so the chain can be
verified later.

Usage:
    from evidence_store import EvidenceStore
    store = EvidenceStore("evidence")
    store.save("comments", rows, url="https://.../comments?...")
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone

_BASE64_BLOB = re.compile(r"^data:[^;]+;base64,(.+)$", re.S)


def _now():
    return datetime.now(timezone.utc).isoformat()


def sanitize(value, blob_threshold=4096):
    """Replace huge inline base64 blobs with a hash+length marker.

    Keeps evidence useful and the repo small while still recording (by hash)
    that the blob existed and was unchanged.
    """
    if isinstance(value, dict):
        return {k: sanitize(v, blob_threshold) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v, blob_threshold) for v in value]
    if isinstance(value, str):
        m = _BASE64_BLOB.match(value)
        if m and len(value) > blob_threshold:
            raw = m.group(1).encode()
            return {
                "_redacted": "base64-blob",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "prefix": value[:32],
            }
    return value


class EvidenceStore:
    def __init__(self, directory):
        self.dir = directory
        self.manifest_path = os.path.join(directory, "manifest.json")
        os.makedirs(directory, exist_ok=True)
        self.manifest = self._load()

    def _load(self):
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, encoding="utf-8") as fh:
                    return json.load(fh)
            except (OSError, ValueError):
                pass
        return {"created_at": _now(), "tables": {}}

    def save(self, name, rows, url="", note="", sanitize_data=False):
        data = sanitize(rows) if sanitize_data else rows
        payload = {
            "name": name,
            "fetched_at": _now(),
            "source_url": url,
            "row_count": len(data) if isinstance(data, list) else 1,
            "rows": data,
        }
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        path = os.path.join(self.dir, f"{name}.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, path)

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        entry = self.manifest["tables"].setdefault(name, {"history": []})
        record = {
            "fetched_at": payload["fetched_at"],
            "source_url": url,
            "row_count": payload["row_count"],
            "sha256": digest,
            "note": note,
        }
        entry["latest"] = {**record, "file": f"{name}.json"}
        entry["history"].append(record)
        self._write_manifest()
        return digest

    def _write_manifest(self):
        self.manifest["updated_at"] = _now()
        tmp = self.manifest_path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            json.dump(self.manifest, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, self.manifest_path)


def verify(directory):
    """Recompute every snapshot hash and compare against the manifest."""
    store = EvidenceStore(directory)
    ok = True
    for name, entry in sorted(store.manifest.get("tables", {}).items()):
        latest = entry.get("latest", {})
        path = os.path.join(directory, latest.get("file", f"{name}.json"))
        if not os.path.exists(path):
            print(f"MISSING  {name}")
            ok = False
            continue
        with open(path, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        match = digest == latest.get("sha256")
        ok = ok and match
        print(f"{'OK      ' if match else 'MISMATCH'} {name:18s} {digest[:16]}")
    return ok


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "evidence")
    sys.exit(0 if verify(target) else 1)
