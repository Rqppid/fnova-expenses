"""OneDrive (personal Microsoft account) via Microsoft Graph.

Auth: a public-client app registration ("Personal Microsoft accounts only", public client
flows allowed). One-time device-code sign-in gives a refresh token; every run exchanges it
for an access token and a NEW refresh token, which the caller must persist (tokens slide
90 days from their last use).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import quote

import requests

AUTHORITY = "https://login.microsoftonline.com/consumers/oauth2/v2.0"
SCOPES = "Files.ReadWrite offline_access User.Read"
GRAPH = "https://graph.microsoft.com/v1.0"
SMALL_UPLOAD = 4 * 1024 * 1024
CHUNK = 320 * 1024 * 10          # upload-session chunks must be multiples of 320 KiB


class GraphError(Exception):
    pass


class ConflictError(GraphError):
    """The remote file changed since we read it (eTag mismatch)."""


# -- auth --------------------------------------------------------------------------------

def device_code_login(client_id: str, show=print) -> dict:
    r = requests.post(f"{AUTHORITY}/devicecode", data={"client_id": client_id, "scope": SCOPES}, timeout=30)
    r.raise_for_status()
    dc = r.json()
    show(dc["message"])
    deadline = time.time() + int(dc.get("expires_in", 900))
    while time.time() < deadline:
        time.sleep(int(dc.get("interval", 5)))
        t = requests.post(f"{AUTHORITY}/token", timeout=30, data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": client_id, "device_code": dc["device_code"]})
        body = t.json()
        if t.ok:
            return body
        if body.get("error") not in ("authorization_pending", "slow_down"):
            raise GraphError(f"Sign-in failed: {body.get('error_description', body)}")
    raise GraphError("Sign-in timed out")


def refresh(client_id: str, refresh_token: str) -> dict:
    """Returns the token response: access_token plus a rotated refresh_token."""
    r = requests.post(f"{AUTHORITY}/token", timeout=30, data={
        "grant_type": "refresh_token", "client_id": client_id,
        "refresh_token": refresh_token, "scope": SCOPES})
    body = r.json()
    if not r.ok:
        raise GraphError(f"Microsoft token refresh failed: {body.get('error_description', body)}")
    return body


# -- drive -------------------------------------------------------------------------------

@dataclass
class Item:
    rel: str             # path relative to the base folder, forward slashes
    id: str
    etag: str
    size: int
    sha1: str | None     # lowercase hex, OneDrive personal provides it for most files
    folder: bool


class OneDrive:
    """All paths are relative to `base` (e.g. 'Desktop/VAT RETURNS')."""

    def __init__(self, access_token: str, base: str):
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {access_token}"
        self.base = base.strip("/")
        self._ids: dict[str, str] = {}

    def _req(self, method: str, url: str, ok=(200, 201, 202, 204), **kw):
        url = url if url.startswith("http") else GRAPH + url
        for attempt in range(5):
            r = self.s.request(method, url, timeout=120, **kw)
            if r.status_code in (429, 503, 504):
                time.sleep(int(r.headers.get("Retry-After", 2 ** attempt)))
                continue
            if r.status_code == 412:
                raise ConflictError(f"{method} {url}: file changed remotely (412)")
            if r.status_code not in ok:
                raise GraphError(f"{method} {url}: {r.status_code} {r.text[:300]}")
            return r
        raise GraphError(f"{method} {url}: throttled")

    def _path_url(self, rel: str) -> str:
        full = "/".join(p for p in (self.base, rel.strip("/")) if p)
        return f"/me/drive/root:/{quote(full)}:"

    def item(self, rel: str) -> dict | None:
        r = self.s.get(GRAPH + self._path_url(rel), timeout=60)
        if r.status_code == 404:
            return None
        if not r.ok:
            raise GraphError(f"GET {rel}: {r.status_code} {r.text[:200]}")
        return r.json()

    def list_tree(self, skip_dirs: set[str] = frozenset()) -> list[Item]:
        root = self.item("")
        if root is None:
            raise GraphError(f"OneDrive folder not found: {self.base}")
        out: list[Item] = []
        stack = [("", root["id"])]
        while stack:
            rel, fid = stack.pop()
            self._ids[rel] = fid
            url = (f"/me/drive/items/{fid}/children?$top=999"
                   "&$select=id,name,eTag,size,file,folder")
            while url:
                data = self._req("GET", url).json()
                for c in data.get("value", []):
                    crel = f"{rel}/{c['name']}".lstrip("/")
                    if "folder" in c:
                        out.append(Item(crel, c["id"], c.get("eTag", ""), 0, None, True))
                        if c["name"] not in skip_dirs and crel not in skip_dirs:
                            stack.append((crel, c["id"]))
                    else:
                        h = (c.get("file") or {}).get("hashes") or {}
                        out.append(Item(crel, c["id"], c.get("eTag", ""), int(c.get("size", 0)),
                                        (h.get("sha1Hash") or "").lower() or None, False))
                url = data.get("@odata.nextLink")
        return out

    def download(self, item_id: str) -> bytes:
        return self._req("GET", f"/me/drive/items/{item_id}/content", allow_redirects=True).content

    def ensure_folder(self, rel: str) -> str:
        rel = rel.strip("/")
        if rel in self._ids:
            return self._ids[rel]
        it = self.item(rel)
        if it is None:
            parent, _, name = rel.rpartition("/")
            pid = self.ensure_folder(parent)
            it = self._req("POST", f"/me/drive/items/{pid}/children", json={
                "name": name, "folder": {}, "@microsoft.graph.conflictBehavior": "fail"}).json()
        self._ids[rel] = it["id"]
        return it["id"]

    def upload_new(self, rel: str, data: bytes) -> dict:
        """Create a file that must not exist yet."""
        parent, _, name = rel.strip("/").rpartition("/")
        pid = self.ensure_folder(parent)
        if len(data) <= SMALL_UPLOAD:
            return self._req("PUT", f"/me/drive/items/{pid}:/{quote(name)}:/content"
                             "?@microsoft.graph.conflictBehavior=fail", data=data).json()
        sess = self._req("POST", f"/me/drive/items/{pid}:/{quote(name)}:/createUploadSession", json={
            "item": {"@microsoft.graph.conflictBehavior": "fail"}}).json()
        return self._chunked(sess["uploadUrl"], data)

    def replace(self, item_id: str, data: bytes, etag: str) -> dict:
        """Overwrite a file only if it is unchanged since we read it (If-Match eTag)."""
        if len(data) <= SMALL_UPLOAD:
            return self._req("PUT", f"/me/drive/items/{item_id}/content", data=data,
                             headers={"If-Match": etag}).json()
        sess = self._req("POST", f"/me/drive/items/{item_id}/createUploadSession",
                         headers={"If-Match": etag}, json={}).json()
        return self._chunked(sess["uploadUrl"], data)

    def _chunked(self, url: str, data: bytes) -> dict:
        total, pos, last = len(data), 0, None
        while pos < total:
            chunk = data[pos:pos + CHUNK]
            r = requests.put(url, data=chunk, timeout=300, headers={
                "Content-Range": f"bytes {pos}-{pos + len(chunk) - 1}/{total}"})
            if r.status_code not in (200, 201, 202):
                raise GraphError(f"upload chunk failed: {r.status_code} {r.text[:200]}")
            pos += len(chunk)
            last = r
        return last.json()

    def move(self, item_id: str, new_rel: str) -> dict:
        parent, _, name = new_rel.strip("/").rpartition("/")
        pid = self.ensure_folder(parent)
        return self._req("PATCH", f"/me/drive/items/{item_id}", json={
            "parentReference": {"id": pid}, "name": name,
            "@microsoft.graph.conflictBehavior": "fail"}).json()
