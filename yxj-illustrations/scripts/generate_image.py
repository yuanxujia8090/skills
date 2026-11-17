#!/usr/bin/env python3
"""Call an OpenAI-shaped image API (text-to-image and single-image edit).

Config, key and endpoint are configurable, no local paths are hard-coded:

  1. environment:  OPENIMAGE_API_KEY, OPENIMAGE_BASE_URL, OPENIMAGE_MODEL,
                   OPENIMAGE_TIMEOUT_MS, OPENIMAGE_KEY_PROVIDER,
                   YXJ_IMAGEGEN_CONFIG (path to a JSON config file)
  2. config file:  $YXJ_IMAGEGEN_CONFIG, else ~/.pi/agent/image-gen.json
  3. built-in defaults (model name and timeout only; baseUrl must be configured)

Any missing or invalid field falls back on its own, so a partial config file
still works. Check the effective values without spending money:

  python3 scripts/generate_image.py --show-config
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import time
import urllib.request
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".pi/agent/image-gen.json"
FALLBACK_CONFIG = {
    "baseUrl": "",
    "model": "gpt-image-2",
    "timeoutMs": 300000,
    "keyProvider": "openimage",
}
DEFAULT_SIZE = "1536x1024"

ENV_MAP = {
    "baseUrl": "OPENIMAGE_BASE_URL",
    "model": "OPENIMAGE_MODEL",
    "timeoutMs": "OPENIMAGE_TIMEOUT_MS",
    "keyProvider": "OPENIMAGE_KEY_PROVIDER",
}


def load_config() -> tuple[dict, str]:
    """Return (config, where it came from). Each field falls back separately."""
    cfg = dict(FALLBACK_CONFIG)
    source = "built-in defaults (no config file read)"
    path = Path(os.environ.get("YXJ_IMAGEGEN_CONFIG") or DEFAULT_CONFIG_PATH)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raw = None
    if isinstance(raw, dict):
        source = str(path)
        if isinstance(raw.get("baseUrl"), str) and raw["baseUrl"].strip():
            cfg["baseUrl"] = raw["baseUrl"].strip().rstrip("/")
        if isinstance(raw.get("model"), str) and raw["model"].strip():
            cfg["model"] = raw["model"].strip()
        timeout = raw.get("timeoutMs")
        if isinstance(timeout, (int, float)) and timeout > 0:
            cfg["timeoutMs"] = int(timeout)
        if isinstance(raw.get("keyProvider"), str) and raw["keyProvider"].strip():
            cfg["keyProvider"] = raw["keyProvider"].strip()

    overridden = []
    for field, env_name in ENV_MAP.items():
        value = os.environ.get(env_name)
        if not value or not value.strip():
            continue
        if field == "timeoutMs":
            try:
                ms = int(float(value))
            except ValueError:
                continue
            if ms <= 0:
                continue
            cfg[field] = ms
        else:
            cfg[field] = value.strip().rstrip("/") if field == "baseUrl" else value.strip()
        overridden.append(env_name)
    if overridden:
        source = f"{source} + env {', '.join(overridden)}"
    return cfg, source


CONFIG, CONFIG_SOURCE = load_config()
BASE_URL = CONFIG["baseUrl"]
MODEL = CONFIG["model"]
TIMEOUT = CONFIG["timeoutMs"]
KEY_PROVIDER = CONFIG["keyProvider"]


def api_key() -> str:
    if os.environ.get("OPENIMAGE_API_KEY"):
        return os.environ["OPENIMAGE_API_KEY"].strip()
    for p in (Path.home() / ".pi/agent/openimage.key", Path.home() / ".pi/agent/auth.json"):
        if not p.exists():
            continue
        if p.suffix == ".key":
            text = p.read_text().strip()
            if text:
                return text
            continue
        try:
            data = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        entry = data.get(KEY_PROVIDER) or {}
        key = entry.get("key") or entry.get("api_key")
        if key:
            return key
    raise SystemExit(
        f"missing key: set OPENIMAGE_API_KEY, or put {KEY_PROVIDER}.key into ~/.pi/agent/auth.json"
    )


def decode_first(payload: dict) -> tuple[bytes, str | None]:
    first = (payload.get("data") or [None])[0] or {}
    revised = first.get("revised_prompt")
    if first.get("b64_json"):
        return base64.b64decode(first["b64_json"]), revised
    url = first.get("url")
    if url:
        if not str(url).startswith(("https://", "http://")):
            raise SystemExit(f"unexpected image url scheme: {str(url)[:80]}")
        with urllib.request.urlopen(url, timeout=120) as res:
            return res.read(), revised
    raise SystemExit(f"no b64_json/url: {json.dumps(payload)[:400]}")


def generate(prompt: str, size: str) -> tuple[bytes, str | None, float]:
    t0 = time.time()
    body = json.dumps({"model": MODEL, "prompt": prompt, "n": 1, "size": size}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/images/generations",
        data=body,
        headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        raw_text = res.read().decode()
    try:
        payload = json.loads(raw_text)
    except ValueError:
        raise SystemExit(f"response is not JSON: {raw_text[:300]}") from None
    raw, revised = decode_first(payload)
    return raw, revised, time.time() - t0


def edit(prompt: str, image_path: Path, size: str) -> tuple[bytes, str | None, float]:
    import requests

    t0 = time.time()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(
        image_path.suffix.lower(), "image/png"
    )
    with image_path.open("rb") as f:
        r = requests.post(
            f"{BASE_URL}/images/edits",
            headers={"Authorization": f"Bearer {api_key()}"},
            data={"model": MODEL, "prompt": prompt, "n": "1", "size": size},
            files={"image": (image_path.name, f, mime)},
            timeout=TIMEOUT,
        )
    if r.status_code >= 400:
        raise SystemExit(f"HTTP {r.status_code}: {r.text[:400]}")
    raw, revised = decode_first(r.json())
    return raw, revised, time.time() - t0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", help="scene description, English works best")
    ap.add_argument("--image", help="reference image for an edit request")
    ap.add_argument("--size", default=DEFAULT_SIZE)
    ap.add_argument("--out")
    ap.add_argument("--show-config", action="store_true", help="print effective config, no API call, no cost")
    args = ap.parse_args()
    if args.show_config:
        print(json.dumps({
            "configSource": CONFIG_SOURCE,
            "baseUrl": BASE_URL or "(unset)",
            "model": MODEL,
            "timeoutMs": TIMEOUT,
            "keyProvider": KEY_PROVIDER,
            "keyFromEnv": bool(os.environ.get("OPENIMAGE_API_KEY")),
        }, ensure_ascii=False, indent=2))
        return
    if not BASE_URL:
        raise SystemExit(
            "missing baseUrl: set OPENIMAGE_BASE_URL, or write baseUrl into "
            f"{os.environ.get('YXJ_IMAGEGEN_CONFIG') or DEFAULT_CONFIG_PATH}"
        )
    if not args.prompt or not args.out:
        ap.error("--prompt and --out are required to generate an image")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.image:
        raw, revised, secs = edit(args.prompt, Path(args.image), args.size)
        mode = "edit"
    else:
        raw, revised, secs = generate(args.prompt, args.size)
        mode = "generate"
    out.write_bytes(raw)
    print(json.dumps({
        "path": str(out),
        "mode": mode,
        "seconds": round(secs, 1),
        "revised_prompt": revised,
        "model": MODEL,
        "size": args.size,
        "bytes": len(raw),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
