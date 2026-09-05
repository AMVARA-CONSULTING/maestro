#!/usr/bin/env python3
"""Maestro hangar CLI for OpenCloud WebDAV (Maestro Space).

Reads credentials from /root/bots/maestro/.env (OPENCLOUD_*).
Never prints tokens or passwords.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ENV_PATH = Path("/root/bots/maestro/.env")
NS = {"d": "DAV:"}

FOLDERS = {
    "human_input": "Files from Luipy / humans for Maestro to read.",
    "maestro_input": "Files Maestro writes for humans / later use.",
    "others": "Misc shared files (neither clear input channel).",
}


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        env[key.strip()] = val
    return env


def creds(env: dict[str, str]) -> tuple[str, str, str, str]:
    url = env.get("OPENCLOUD_URL", "https://cloud.km0digital.com").rstrip("/")
    user = env["OPENCLOUD_USER"]
    token = env.get("OPENCLOUD_APP_TOKEN") or env.get("OPENCLOUD_PASSWORD")
    space = env["OPENCLOUD_SPACE_ID"]
    if not token:
        raise SystemExit("Missing OPENCLOUD_APP_TOKEN (and no OPENCLOUD_PASSWORD fallback)")
    return url, user, token, space


def auth_header(user: str, token: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{token}".encode()).decode()


def dav_base(url: str, space: str) -> str:
    return f"{url}/remote.php/dav/spaces/{space}/"


def normalize_rel(path: str) -> str:
    p = path.strip().lstrip("/")
    return p


def request(
    method: str,
    url: str,
    auth: str,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 120,
    *,
    allow_statuses: set[int] | None = None,
) -> tuple[int, bytes]:
    hdrs = {"Authorization": auth}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read()
        if allow_statuses and exc.code in allow_statuses:
            return exc.code, body
        raise SystemExit(f"HTTP {exc.code} {method} {url}: {body[:300]!r}") from exc


def cmd_folders(_: argparse.Namespace) -> int:
    for name, purpose in FOLDERS.items():
        print(f"{name}\t{purpose}")
    return 0


def cmd_ls(args: argparse.Namespace) -> int:
    env = load_env()
    url, user, token, space = creds(env)
    auth = auth_header(user, token)
    rel = normalize_rel(args.path or "")
    target = dav_base(url, space) + urllib.parse.quote(rel)
    if rel and not rel.endswith("/"):
        # allow listing a folder without trailing slash
        pass
    if rel and not target.endswith("/") and args.path.endswith("/"):
        target += "/"
    elif rel and not Path(rel).suffix and not target.endswith("/"):
        # treat bare folder names as directories
        if rel.rstrip("/") in FOLDERS or rel.endswith("/"):
            target = target.rstrip("/") + "/"

    propfind = (
        b'<?xml version="1.0"?>'
        b'<d:propfind xmlns:d="DAV:">'
        b"<d:prop><d:displayname/><d:resourcetype/>"
        b"<d:getcontentlength/><d:getcontenttype/><d:getlastmodified/>"
        b"</d:prop></d:propfind>"
    )
    status, body = request(
        "PROPFIND",
        target if target.endswith("/") or not rel else target,
        auth,
        data=propfind,
        headers={"Depth": "1", "Content-Type": "application/xml"},
    )
    if status not in (207, 200):
        raise SystemExit(f"Unexpected status {status}")

    root = ET.fromstring(body)
    rows = []
    for resp in root.findall("d:response", NS):
        href = resp.findtext("d:href", default="", namespaces=NS)
        name = urllib.parse.unquote(href.rstrip("/").split("/")[-1])
        rtype = resp.find("d:propstat/d:prop/d:resourcetype", NS)
        is_dir = rtype is not None and rtype.find("d:collection", NS) is not None
        length = resp.findtext("d:propstat/d:prop/d:getcontentlength", default="", namespaces=NS)
        ctype = resp.findtext("d:propstat/d:prop/d:getcontenttype", default="", namespaces=NS)
        mod = resp.findtext("d:propstat/d:prop/d:getlastmodified", default="", namespaces=NS)
        if not name:
            continue
        # skip the listed folder itself when href ends with the folder
        rows.append((is_dir, name, length, ctype, mod, href))

    # drop self entry (first collection matching request path basename)
    if rows and rows[0][0]:
        self_name = urllib.parse.unquote(rel.rstrip("/").split("/")[-1]) if rel else space.split("$")[-1]
        if rows[0][1] == self_name or rows[0][1] == space.split("$")[-1]:
            rows = rows[1:]

    if args.json:
        out = [
            {
                "name": n,
                "type": "dir" if d else "file",
                "size": int(length) if length else None,
                "content_type": ctype or None,
                "modified": mod or None,
            }
            for d, n, length, ctype, mod, _ in rows
            if n != ".space"
        ]
        print(json.dumps(out, indent=2))
        return 0

    for is_dir, name, length, ctype, mod, _ in rows:
        if name == ".space":
            continue
        kind = "DIR" if is_dir else "FILE"
        print(f"{kind}\t{name}\t{length}\t{ctype}\t{mod}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    env = load_env()
    url, user, token, space = creds(env)
    auth = auth_header(user, token)
    rel = normalize_rel(args.remote)
    if not rel or rel.endswith("/"):
        raise SystemExit("Remote path must be a file")
    target = dav_base(url, space) + urllib.parse.quote(rel)
    status, body = request("GET", target, auth)
    out = Path(args.output) if args.output else Path.cwd() / Path(rel).name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)
    print(f"OK\t{out}\t{len(body)}\tbytes")
    return 0


def cmd_put(args: argparse.Namespace) -> int:
    env = load_env()
    url, user, token, space = creds(env)
    auth = auth_header(user, token)
    local = Path(args.local)
    if not local.is_file():
        raise SystemExit(f"Local file not found: {local}")
    rel = normalize_rel(args.remote)
    if not rel or rel.endswith("/"):
        raise SystemExit("Remote path must include filename")
    # Ensure parent folders exist (MKCOL; ignore already-exists).
    parts = rel.split("/")[:-1]
    base = dav_base(url, space)
    built = ""
    for part in parts:
        built = f"{built}{part}/"
        mk = base + urllib.parse.quote(built)
        request("MKCOL", mk, auth, allow_statuses={201, 405, 409})

    ctype = mimetypes.guess_type(str(local))[0] or "application/octet-stream"
    data = local.read_bytes()
    target = base + urllib.parse.quote(rel)
    status, _ = request(
        "PUT",
        target,
        auth,
        data=data,
        headers={"Content-Type": ctype},
        allow_statuses={200, 201, 204},
    )
    if status not in (200, 201, 204):
        raise SystemExit(f"Unexpected PUT status {status}")
    print(f"OK\t{rel}\t{len(data)}\tbytes\tHTTP {status}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Maestro OpenCloud Space hangar CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("folders", help="Show hangar folder purposes")
    s.set_defaults(func=cmd_folders)

    s = sub.add_parser("ls", help="List a path inside Maestro Space")
    s.add_argument("path", nargs="?", default="", help="Relative path (e.g. human_input/)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_ls)

    s = sub.add_parser("get", help="Download a file from the Space")
    s.add_argument("remote", help="Remote relative path")
    s.add_argument("-o", "--output", help="Local output path")
    s.set_defaults(func=cmd_get)

    s = sub.add_parser("put", help="Upload a local file into the Space")
    s.add_argument("local", help="Local file path")
    s.add_argument("remote", help="Remote relative path including filename")
    s.set_defaults(func=cmd_put)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
